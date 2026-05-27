import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, UnauthorizedError
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.ai_interaction import AIInteraction
from app.models.conversation import Conversation
from app.models.daily_summary import DailySummary
from app.models.embedding import Embedding
from app.models.feedback import FeedbackItem, MemoryFeedback, UsageEvent
from app.models.memory import Memory
from app.models.message import Message
from app.models.note import Note
from app.models.password_reset_token import PasswordResetToken
from app.models.project import Project
from app.models.project_context import ProjectContext
from app.models.refresh_token import RefreshToken
from app.models.launch import InviteCode
from app.models.task import Task
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import SignupRequest, TokenResponse
from app.services.email_service import EmailService
from app.services.starter_workspace_service import StarterWorkspaceService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def signup(self, data: SignupRequest) -> tuple[TokenResponse, User]:
        from app.core.config import get_settings

        existing = await self.session.execute(
            select(User).where(User.email == data.email.lower(), User.deleted_at.is_(None))
        )
        if existing.scalar_one_or_none():
            raise AppError("Email already registered", status_code=409, code="email_exists")

        invite = await self._validate_invite(data.email.lower(), data.invite_code)
        user = User(
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            display_name=data.display_name,
            avatar_url=None,
            onboarding_state="new",
            timezone="UTC",
            is_verified=False,
            is_active=not get_settings().invite_required or invite is not None,
        )
        self.session.add(user)
        await self.session.flush()
        if invite:
            invite.use_count += 1
            if invite.use_count >= invite.max_uses:
                invite.is_active = False
        self.session.add(
            UserProfile(
                user_id=user.id,
                display_name=data.display_name,
                avatar_url=None,
                onboarding_completed=False,
                communication_style="balanced",
                timezone="UTC",
                profile_metadata={},
                communication_preferences={"style": "direct", "response_depth": "balanced"},
            )
        )
        await StarterWorkspaceService(self.session).ensure_for_user(user)
        tokens = await self._issue_tokens(user.id)
        return tokens, user

    async def _validate_invite(self, email: str, code: str | None) -> InviteCode | None:
        from app.core.config import get_settings

        settings = get_settings()
        if not settings.invite_required and not code:
            return None
        if not code:
            raise AppError("An invite code is required for early access", status_code=403, code="invite_required")
        result = await self.session.execute(select(InviteCode).where(InviteCode.code == code, InviteCode.is_active.is_(True)))
        invite = result.scalar_one_or_none()
        if not invite or invite.use_count >= invite.max_uses:
            raise AppError("Invite code is invalid or has already been used", status_code=403, code="invalid_invite")
        if invite.email and invite.email.lower() != email:
            raise AppError("Invite code is assigned to a different email", status_code=403, code="invite_email_mismatch")
        return invite

    async def login(self, email: str, password: str) -> tuple[TokenResponse, User]:
        result = await self.session.execute(
            select(User).where(User.email == email.lower(), User.deleted_at.is_(None))
        )
        user = result.scalar_one_or_none()
        if not user or not user.password_hash or not verify_password(password, user.password_hash):
            raise AppError("Invalid login credentials", status_code=401, code="invalid_credentials")
        if not user.is_active:
            raise UnauthorizedError("Account is inactive")
        return await self._issue_tokens(user.id), user

    async def forgot_password(self, email: str) -> None:
        normalized = email.lower()
        result = await self.session.execute(
            select(User).where(User.email == normalized, User.deleted_at.is_(None), User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        now = datetime.now(timezone.utc)
        await self.session.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
            .values(used_at=now)
        )
        plain_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        settings = get_settings()
        expires = now + timedelta(minutes=settings.password_reset_expire_minutes)
        self.session.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires))

        reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={plain_token}"
        EmailService().send_password_reset(
            email=user.email,
            reset_url=reset_url,
            expires_minutes=settings.password_reset_expire_minutes,
        )

    async def reset_password(self, token: str, password: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        result = await self.session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
            )
        )
        reset_token = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not reset_token:
            raise AppError(
                "Invalid password reset token",
                status_code=400,
                code="invalid_reset_token",
                user_message="That reset link is not valid. Please request a new one.",
            )
        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise AppError(
                "Expired password reset token",
                status_code=400,
                code="expired_reset_token",
                user_message="That reset link has expired. Please request a new one.",
            )

        user = await self.session.get(User, reset_token.user_id)
        if not user or user.deleted_at or not user.is_active:
            raise AppError(
                "Password reset user unavailable",
                status_code=400,
                code="invalid_reset_token",
                user_message="That reset link is not valid. Please request a new one.",
            )

        user.password_hash = hash_password(password)
        if user.auth_provider == "google":
            user.auth_provider = "email"
        reset_token.used_at = now
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    async def delete_account(self, user: User, password: str | None, confirmation: str) -> None:
        if confirmation.strip().upper() != "DELETE":
            raise AppError(
                "Account deletion confirmation mismatch",
                status_code=400,
                code="invalid_request",
                user_message="Type DELETE to confirm account deletion.",
            )
        if user.password_hash:
            if not password or not verify_password(password, user.password_hash):
                raise AppError(
                    "Password confirmation failed",
                    status_code=401,
                    code="invalid_credentials",
                    user_message="The password confirmation did not match.",
                )

        conversation_ids = select(Conversation.id).where(Conversation.user_id == user.id)
        project_ids = select(Project.id).where(Project.user_id == user.id)

        await self.session.execute(delete(FeedbackItem).where(FeedbackItem.user_id == user.id))
        await self.session.execute(delete(MemoryFeedback).where(MemoryFeedback.user_id == user.id))
        await self.session.execute(delete(UsageEvent).where(UsageEvent.user_id == user.id))
        await self.session.execute(delete(AIInteraction).where(AIInteraction.user_id == user.id))
        await self.session.execute(delete(Message).where(Message.conversation_id.in_(conversation_ids)))
        await self.session.execute(delete(ProjectContext).where(ProjectContext.project_id.in_(project_ids)))
        await self.session.execute(delete(Memory).where(Memory.user_id == user.id))
        await self.session.execute(delete(Embedding).where(Embedding.user_id == user.id))
        await self.session.execute(delete(Task).where(Task.user_id == user.id))
        await self.session.execute(delete(Note).where(Note.user_id == user.id))
        await self.session.execute(delete(DailySummary).where(DailySummary.user_id == user.id))
        await self.session.execute(delete(Conversation).where(Conversation.user_id == user.id))
        await self.session.execute(delete(Project).where(Project.user_id == user.id))
        await self.session.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
        await self.session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id))
        await self.session.execute(delete(UserProfile).where(UserProfile.user_id == user.id))
        await self.session.delete(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, "refresh")
        user_id = UUID(payload["sub"])
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        stored = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if not stored:
            raise UnauthorizedError("Refresh token invalid or expired")

        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            raise UnauthorizedError("Refresh token invalid or expired")

        stored.revoked_at = now
        return await self._issue_tokens(user_id)

    async def logout(self, user_id: UUID, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        stored = result.scalar_one_or_none()
        if stored:
            stored.revoked_at = datetime.now(timezone.utc)

    async def _issue_tokens(self, user_id: UUID) -> TokenResponse:
        jti = str(uuid4())
        refresh = create_refresh_token(user_id, jti)
        token_hash = hashlib.sha256(refresh.encode()).hexdigest()
        from app.core.config import get_settings

        settings = get_settings()
        expires = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        self.session.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires))
        return TokenResponse(access_token=create_access_token(user_id), refresh_token=refresh)

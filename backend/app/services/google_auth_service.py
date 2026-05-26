"""Google Sign-In — verify ID tokens and issue Synzept JWTs."""

import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, UnauthorizedError
from app.models.user import User
from app.models.user_profile import UserProfile
from app.schemas.auth import TokenResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
settings = get_settings()


class GoogleAuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.auth = AuthService(session)

    async def login_with_google(self, id_token_str: str) -> tuple[TokenResponse, User]:
        if not settings.google_client_id:
            raise AppError("Google sign-in is not configured", status_code=503, code="google_not_configured")

        try:
            payload = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                settings.google_client_id,
            )
        except Exception as exc:
            logger.warning("Google token verification failed: %s", exc)
            raise UnauthorizedError("Invalid Google token") from exc

        google_sub = payload.get("sub")
        email = (payload.get("email") or "").lower()
        email_verified = payload.get("email_verified")
        name = payload.get("name")
        picture = payload.get("picture")

        if not google_sub or not email:
            raise UnauthorizedError("Google account missing email")
        if email_verified is not True:
            raise UnauthorizedError("Google email is not verified")

        user = await self._find_user(google_sub, email)

        if not user:
            user = User(
                email=email,
                password_hash=None,
                google_id=google_sub,
                auth_provider="google",
                display_name=name,
                avatar_url=picture,
                onboarding_state="new",
                is_verified=True,
            )
            self.session.add(user)
            await self.session.flush()
            self.session.add(
                UserProfile(
                    user_id=user.id,
                    display_name=name,
                    avatar_url=picture,
                    onboarding_completed=False,
                    communication_style="balanced",
                    timezone="UTC",
                    profile_metadata={},
                    communication_preferences={"style": "direct", "response_depth": "balanced"},
                )
            )
        else:
            if user.google_id and user.google_id != google_sub:
                raise UnauthorizedError("Google account does not match this email")
            if not user.google_id:
                user.google_id = google_sub
            if user.auth_provider == "email":
                user.auth_provider = "google"
            if name and not user.display_name:
                user.display_name = name
            if picture:
                user.avatar_url = picture
            user.is_verified = True
            if not user.is_active:
                raise UnauthorizedError("Account is inactive")
            await self._ensure_profile(user, name, picture)

        tokens = await self.auth._issue_tokens(user.id)
        return tokens, user

    async def _find_user(self, google_id: str, email: str) -> User | None:
        by_google = await self.session.execute(
            select(User).where(User.google_id == google_id, User.deleted_at.is_(None))
        )
        user = by_google.scalar_one_or_none()
        if user:
            return user

        result = await self.session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def _ensure_profile(self, user: User, name: str | None, picture: str | None) -> None:
        result = await self.session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
        profile = result.scalar_one_or_none()
        if profile:
            if picture and not profile.avatar_url:
                profile.avatar_url = picture
            return
        self.session.add(
            UserProfile(
                user_id=user.id,
                display_name=user.display_name or name,
                avatar_url=user.avatar_url or picture,
                onboarding_completed=user.onboarding_state == "complete",
                communication_style="balanced",
                timezone=user.timezone or "UTC",
                profile_metadata={},
                communication_preferences={"style": "direct", "response_depth": "balanced"},
            )
        )

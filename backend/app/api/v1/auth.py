import logging
import traceback

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import (
    AvatarUpdate,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    ProfileOut,
    ProfileUpdate,
    RefreshRequest,
    ResetPasswordRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
    UserPreferencesUpdate,
)
from app.schemas.onboarding import AuthResponse, GoogleAuthIn
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.google_auth_service import GoogleAuthService
from app.services.usage_event_service import UsageEventService
from app.services.user_profile_service import UserProfileService
from app.services.account_data_export_service import AccountDataExportService

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)
settings = get_settings()


def _auth_response(tokens: TokenResponse, user: User) -> AuthResponse:
    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        onboarding_state=user.onboarding_state,
        display_name=user.display_name,
    )


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest, session: AsyncSession = Depends(get_db)):
    tokens, user = await AuthService(session).signup(body)
    await UsageEventService(session).track(user_id=user.id, event_type="signup_completed", surface="auth", metadata={"provider": "email"})
    return _auth_response(tokens, user)


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(get_db)):
    tokens, user = await AuthService(session).login(body.email, body.password)
    await UsageEventService(session).track(user_id=user.id, event_type="login_completed", surface="auth", metadata={"provider": "email"})
    return _auth_response(tokens, user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest, session: AsyncSession = Depends(get_db)):
    await AuthService(session).forgot_password(body.email)
    return {
        "ok": True,
        "message": "If that email belongs to a Synzept account, a reset link is on its way.",
    }


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest, session: AsyncSession = Depends(get_db)):
    await AuthService(session).reset_password(body.token, body.password)
    return {"ok": True, "message": "Your password has been updated. You can sign in now."}


@router.post("/google", response_model=AuthResponse)
async def google_login(body: GoogleAuthIn, session: AsyncSession = Depends(get_db)):
    logger.info(
        "Google OAuth environment: GOOGLE_CLIENT_ID=%s GOOGLE_CLIENT_SECRET=%s FRONTEND_URL=%s JWT_SECRET_KEY=%s",
        "present" if settings.google_client_id else "missing",
        "present" if settings.google_client_secret else "missing",
        "present" if settings.frontend_url else "missing",
        "present" if settings.jwt_secret_key and settings.jwt_secret_key != "dev-only-change-me" else "missing",
    )
    try:
        tokens, user = await GoogleAuthService(session).login_with_google(body.id_token)
        await UsageEventService(session).track(user_id=user.id, event_type="login_completed", surface="auth", metadata={"provider": "google"})
        return _auth_response(tokens, user)
    except Exception:
        logger.exception("Google OAuth failed")
        logger.debug("Google OAuth traceback:\n%s", traceback.format_exc())
        raise


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(get_db)):
    return await AuthService(session).refresh(body.refresh_token)


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, session: AsyncSession = Depends(get_db)):
    return await AuthService(session).refresh(body.refresh_token)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await AuthService(session).logout(user.id, body.refresh_token)
    return {"ok": True}


async def _user_out(user: User, session: AsyncSession) -> dict:
    billing = await BillingService(session).overview(user)
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "profile_summary": user.profile_summary,
        "onboarding_state": user.onboarding_state,
        "auth_provider": user.auth_provider,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "preferences": user.preferences or {},
        "plan_type": billing["plan"]["planType"],
        "subscription_status": billing["plan"]["status"],
        "is_pro": billing["plan"]["isPro"],
    }


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await _user_out(user, session)


@router.get("/current-user", response_model=UserOut)
async def current_user(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await _user_out(user, session)


@router.patch("/preferences", response_model=UserOut)
async def update_preferences(
    body: UserPreferencesUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    prefs = dict(user.preferences or {})
    if body.memory_enabled is not None:
        prefs["memory_enabled"] = body.memory_enabled
    if body.personalization_enabled is not None:
        prefs["personalization_enabled"] = body.personalization_enabled
    if body.analytics_enabled is not None:
        prefs["analytics_enabled"] = body.analytics_enabled
    user.preferences = prefs
    return await _user_out(user, session)


@router.get("/profile", response_model=ProfileOut)
async def profile(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await UserProfileService(session).get_or_create(user.id)


@router.patch("/profile", response_model=UserOut)
async def update_profile(
    body: ProfileUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await UserProfileService(session).update_profile(user, body)
    return await _user_out(user, session)


@router.get("/export")
async def export_account_data(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await AccountDataExportService(session).export(user)


@router.patch("/profile/avatar", response_model=UserOut)
async def update_avatar(
    body: AvatarUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await UserProfileService(session).update_avatar(user, body.avatar_url)
    return await _user_out(user, session)


@router.delete("/account", response_model=MessageResponse)
async def delete_account(
    body: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    await AuthService(session).delete_account(user, body.password, body.confirmation)
    return {"ok": True, "message": "Your account and workspace data have been deleted."}

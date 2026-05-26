from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import ORMModel


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=120)
    invite_code: str | None = Field(default=None, max_length=64)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=24, max_length=256)
    password: str = Field(min_length=8, max_length=128)


class DeleteAccountRequest(BaseModel):
    password: str | None = Field(default=None, max_length=128)
    confirmation: str = Field(min_length=6, max_length=32)


class MessageResponse(BaseModel):
    ok: bool = True
    message: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ProfileOut(ORMModel):
    user_id: UUID
    display_name: str | None = None
    avatar_url: str | None = None
    onboarding_completed: bool = False
    communication_style: str = "balanced"
    timezone: str = "UTC"
    profile_metadata: dict = Field(default_factory=dict)
    goals: list = Field(default_factory=list)


class UserOut(ORMModel):
    id: UUID
    email: str
    display_name: str | None
    avatar_url: str | None = None
    profile_summary: str | None
    onboarding_state: str = "new"
    auth_provider: str = "email"
    is_active: bool = True
    is_verified: bool = False
    preferences: dict = Field(default_factory=dict)


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class UserPreferencesUpdate(BaseModel):
    memory_enabled: bool | None = None
    personalization_enabled: bool | None = None
    analytics_enabled: bool | None = None


class AvatarUpdate(BaseModel):
    avatar_url: str | None = Field(default=None, max_length=2_100_000)

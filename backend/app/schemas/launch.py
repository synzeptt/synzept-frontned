from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import ORMModel


class WaitlistJoin(BaseModel):
    email: EmailStr
    name: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    intended_use: str | None = Field(default=None, max_length=1000)
    source: str | None = Field(default="early_access", max_length=120)


class WaitlistOut(ORMModel):
    id: UUID
    email: str
    status: str
    created_at: datetime


class InviteCreate(BaseModel):
    email: EmailStr | None = None
    max_uses: int = Field(default=1, ge=1, le=25)
    notes: str | None = Field(default=None, max_length=1000)


class InviteOut(ORMModel):
    id: UUID
    code: str
    email: str | None
    max_uses: int
    use_count: int
    is_active: bool
    created_at: datetime


class FirstUserSessionOut(BaseModel):
    user_id: UUID
    email: str
    display_name: str | None = None
    onboarding_state: str
    created_at: datetime
    last_activity_at: datetime | None = None
    session_events: int = 0
    feedback_items: int = 0
    interview_completed: bool = False
    confusing_moments: list[str] = Field(default_factory=list)
    exciting_moments: list[str] = Field(default_factory=list)
    drop_off_points: list[str] = Field(default_factory=list)
    tomorrow_answer: str | None = None


class FirstUsersLaunchOut(BaseModel):
    target_users: int = 10
    invited_users: int = 0
    accepted_invites: int = 0
    signed_up_users: int = 0
    active_users: int = 0
    completed_onboarding: int = 0
    interviews_completed: int = 0
    sessions_watched: int = 0
    invite_url_base: str
    invites: list[InviteOut] = Field(default_factory=list)
    first_users: list[FirstUserSessionOut] = Field(default_factory=list)


class AccessStatus(BaseModel):
    early_access_enabled: bool
    invite_required: bool

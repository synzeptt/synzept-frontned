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


class AccessStatus(BaseModel):
    early_access_enabled: bool
    invite_required: bool


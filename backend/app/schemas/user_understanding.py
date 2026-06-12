from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class UserUnderstandingCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=4000)
    source: Literal["user"] = "user"
    confidence: float | None = Field(default=None, ge=0, le=1)


class UserUnderstandingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    value: str | None = Field(default=None, min_length=1, max_length=4000)
    source: Literal["user", "learned"] | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class UserUnderstandingOut(ORMModel):
    id: UUID
    user_id: UUID
    category: str
    title: str
    value: str
    source: Literal["user", "learned"]
    confidence: float | None = None
    learned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

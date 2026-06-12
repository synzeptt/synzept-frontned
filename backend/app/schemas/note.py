from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import TimestampedSchema


class NoteCreate(BaseModel):
    title: str | None = None
    content: str = Field(min_length=1)
    project_id: UUID | None = None
    goal_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    project_id: UUID | None = None
    goal_id: UUID | None = None
    tags: list[str] | None = None
    summary: str | None = None


class NoteOut(TimestampedSchema):
    id: UUID
    title: str | None
    content: str
    project_id: UUID | None
    goal_id: UUID | None
    tags: list[str] = Field(default_factory=list)
    summary: str | None = None

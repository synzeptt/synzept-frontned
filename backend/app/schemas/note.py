from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import TimestampedSchema


class NoteCreate(BaseModel):
    title: str | None = None
    content: str = Field(min_length=1)
    project_id: UUID | None = None
    summary: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    project_id: UUID | None = None
    summary: str | None = None


class NoteOut(TimestampedSchema):
    id: UUID
    title: str | None
    content: str
    project_id: UUID | None
    summary: str | None = None

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import TimestampedSchema
from app.schemas.chat import ConversationOut
from app.schemas.memory import MemoryOut
from app.schemas.note import NoteOut
from app.schemas.task import TaskOut


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    context_summary: str | None = None


class ProjectOut(TimestampedSchema):
    id: UUID
    name: str
    description: str | None
    status: str
    context_summary: str | None


class ProjectContextOut(BaseModel):
    project: ProjectOut
    conversations: list[ConversationOut]
    notes: list[NoteOut]
    tasks: list[TaskOut]
    memories: list[MemoryOut]
    continuity_summary: str

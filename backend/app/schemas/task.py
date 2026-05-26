from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

TASK_STATUSES = {"todo", "in_progress", "completed", "archived"}
TASK_STATUS_ALIASES = {"pending": "todo", "done": "completed"}
TASK_PRIORITIES = {"low", "medium", "high"}


def normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = TASK_STATUS_ALIASES.get(value, value)
    if normalized not in TASK_STATUSES:
        raise ValueError("status must be todo, in_progress, completed, or archived")
    return normalized


def normalize_priority(value: str | None) -> str | None:
    if value is None:
        return None
    if value not in TASK_PRIORITIES:
        raise ValueError("priority must be low, medium, or high")
    return value

from app.schemas.base import TimestampedSchema


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    priority: str = "medium"
    project_id: UUID | None = None
    due_at: datetime | None = None

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        return normalize_priority(value) or "medium"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    due_at: datetime | None = None
    project_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        return normalize_status(value)

    @field_validator("priority")
    @classmethod
    def validate_optional_priority(cls, value: str | None) -> str | None:
        return normalize_priority(value)


class TaskOut(TimestampedSchema):
    id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    project_id: UUID | None
    due_at: datetime | None

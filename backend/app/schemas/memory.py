from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    category: str = "other"
    memory_type: str = "long_term"
    project_id: UUID | None = None
    importance: float = Field(default=0.5, ge=0, le=1)


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    category: str | None = None
    importance: float | None = Field(default=None, ge=0, le=1)


class MemoryOut(ORMModel):
    id: UUID
    content: str
    category: str
    memory_type: str
    importance: float
    project_id: UUID | None
    created_at: datetime

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
    pinned: bool = False
    archived: bool = False


class MemoryUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    category: str | None = None
    importance: float | None = Field(default=None, ge=0, le=1)
    pinned: bool | None = None
    archived: bool | None = None
    reason: str | None = Field(default=None, max_length=500)


class MemoryOut(ORMModel):
    id: UUID
    content: str
    category: str | None
    memory_type: str
    source: str
    confidence: float
    summary: str | None = None
    importance: float
    importance_score: float
    version: int
    project_id: UUID | None
    pinned: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ConnectedEntityOut(BaseModel):
    id: UUID
    title: str
    type: str


class MemoryRevisionOut(BaseModel):
    id: UUID
    version: int
    action: str
    content: str
    category: str
    importance_score: float
    created_at: datetime
    reason: str = ""
    caused_by: str = "system"


class MemoryTrustEventOut(BaseModel):
    id: UUID
    memory_id: UUID | None = None
    action: str
    reason: str
    caused_by_type: str
    caused_by_id: UUID | None = None
    before: dict = Field(default_factory=dict)
    after: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime


class MemoryExplorerItemOut(BaseModel):
    memory: MemoryOut
    connected_projects: list[ConnectedEntityOut] = Field(default_factory=list)
    connected_goals: list[ConnectedEntityOut] = Field(default_factory=list)
    timeline: list[MemoryTrustEventOut] = Field(default_factory=list)


class MemoryMergeIn(BaseModel):
    source_memory_id: UUID
    reason: str | None = Field(default=None, max_length=500)


class MemoryExplainOut(BaseModel):
    message_id: UUID
    memories_used: list[MemoryOut] = Field(default_factory=list)
    projects_used: list[ConnectedEntityOut] = Field(default_factory=list)
    open_loops_used: list[ConnectedEntityOut] = Field(default_factory=list)
    decisions_used: list[ConnectedEntityOut] = Field(default_factory=list)
    explanation: str = ""


class UserMemoryProfile(BaseModel):
    userId: str
    goals: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    long_term_plans: list[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)
    memories: list[MemoryOut] = Field(default_factory=list)

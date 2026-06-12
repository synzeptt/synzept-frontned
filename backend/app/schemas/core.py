from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class CoreProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: str = Field(default="active", max_length=50)


class CoreProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = Field(default=None, max_length=50)


class CoreProjectOut(ORMModel):
    id: UUID
    user_id: UUID
    title: str
    description: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class CoreGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    status: Literal["active", "completed", "paused"] = "active"
    target_date: date | None = None


class CoreGoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    status: Literal["active", "completed", "paused"] | None = None
    target_date: date | None = None


class CoreGoalOut(ORMModel):
    id: UUID
    user_id: UUID
    title: str
    description: str
    status: str
    target_date: date | None
    created_at: datetime


class CoreMemoryCreate(BaseModel):
    memory_type: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(default=1.0, ge=0, le=1)
    source: str = Field(default="manual", min_length=1, max_length=80)


class CoreMemoryUpdate(BaseModel):
    memory_type: str | None = Field(default=None, min_length=1, max_length=50)
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source: str | None = Field(default=None, min_length=1, max_length=80)


class CoreMemoryOut(ORMModel):
    id: UUID
    user_id: UUID
    memory_type: str
    content: str
    confidence: float
    source: str
    created_at: datetime


class TimelineEventCreate(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    importance: float = Field(default=0.5, ge=0, le=1)
    event_date: date


class TimelineEventUpdate(BaseModel):
    event_type: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    importance: float | None = Field(default=None, ge=0, le=1)
    event_date: date | None = None


class TimelineEventOut(ORMModel):
    id: UUID
    user_id: UUID
    event_type: str
    title: str
    description: str
    importance: float
    event_date: date


class LearningSignalCreate(BaseModel):
    signal_type: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=4000)
    confidence: float = Field(default=0.5, ge=0, le=1)
    status: Literal["pending", "accepted", "ignored"] = "pending"


class LearningSignalUpdate(BaseModel):
    signal_type: str | None = Field(default=None, min_length=1, max_length=80)
    content: str | None = Field(default=None, min_length=1, max_length=4000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: Literal["pending", "accepted", "ignored"] | None = None


class LearningSignalOut(ORMModel):
    id: UUID
    user_id: UUID
    signal_type: str
    content: str
    confidence: float
    status: str


class GraphNodeCreate(BaseModel):
    node_type: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)


class GraphNodeUpdate(BaseModel):
    node_type: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=300)


class GraphNodeOut(ORMModel):
    id: UUID
    user_id: UUID
    node_type: str
    title: str


class GraphEdgeCreate(BaseModel):
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: str = Field(min_length=1, max_length=100)
    strength: float = Field(default=0.5, ge=0, le=1)


class GraphEdgeUpdate(BaseModel):
    relationship_type: str | None = Field(default=None, min_length=1, max_length=100)
    strength: float | None = Field(default=None, ge=0, le=1)


class GraphEdgeOut(ORMModel):
    id: UUID
    user_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: str
    strength: float

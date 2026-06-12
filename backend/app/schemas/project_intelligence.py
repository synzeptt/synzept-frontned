from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class ProjectIntelligenceUpdate(BaseModel):
    current_focus: str | None = Field(default=None, max_length=4000)
    summary: str | None = Field(default=None, max_length=4000)
    recommended_next_step: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "paused", "completed"] | None = None


class ProjectIntelligenceOut(ORMModel):
    id: UUID
    project_id: UUID
    current_focus: str
    summary: str
    recommended_next_step: str
    status: Literal["active", "paused", "completed"]
    created_at: datetime
    updated_at: datetime


class ProjectDecisionCreate(BaseModel):
    decision: str = Field(min_length=1, max_length=1000)


class ProjectDecisionUpdate(BaseModel):
    decision: str | None = Field(default=None, min_length=1, max_length=1000)
    status: Literal["open", "resolved"] | None = None


class ProjectDecisionOut(ORMModel):
    id: UUID
    project_id: UUID
    decision: str
    status: Literal["open", "resolved"]
    created_at: datetime


class ProjectOpenLoopCreate(BaseModel):
    loop: str = Field(min_length=1, max_length=1000)


class ProjectOpenLoopUpdate(BaseModel):
    loop: str | None = Field(default=None, min_length=1, max_length=1000)
    status: Literal["open", "closed"] | None = None


class ProjectOpenLoopOut(ORMModel):
    id: UUID
    project_id: UUID
    loop: str
    status: Literal["open", "closed"]
    created_at: datetime


class ProjectActivityOut(BaseModel):
    id: UUID
    type: Literal["conversation", "note", "memory", "task"]
    title: str
    detail: str | None = None
    occurred_at: datetime


class RelatedConversationOut(BaseModel):
    id: UUID
    title: str
    summary: str | None = None
    updated_at: datetime


class RelatedMemoryOut(BaseModel):
    id: UUID
    title: str
    content: str
    updated_at: datetime


class ProjectRiskOut(BaseModel):
    level: Literal["low", "medium", "high"]
    reasons: list[str] = Field(default_factory=list)


class ProjectIntelligencePageOut(BaseModel):
    project_id: UUID
    project_name: str
    project_summary: str
    status: Literal["active", "paused", "completed"]
    last_activity: datetime
    current_focus: str
    recommended_next_step: str
    recent_activity: list[ProjectActivityOut] = Field(default_factory=list)
    decisions: list[ProjectDecisionOut] = Field(default_factory=list)
    open_loops: list[ProjectOpenLoopOut] = Field(default_factory=list)
    conversations: list[RelatedConversationOut] = Field(default_factory=list)
    memories: list[RelatedMemoryOut] = Field(default_factory=list)
    risk: ProjectRiskOut

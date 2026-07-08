from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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


class UserUnderstandingProfileOut(ORMModel):
    user_id: UUID
    current_mission: list[str] = Field(default_factory=list)
    current_focus: list[str] = Field(default_factory=list)
    active_projects: list[str] = Field(default_factory=list)
    open_loops: list[str] = Field(default_factory=list)
    recent_progress: list[str] = Field(default_factory=list)
    recent_decisions: list[str] = Field(default_factory=list)
    next_suggested_actions: list[str] = Field(default_factory=list)
    updated_at: datetime | None = None


class UserUnderstandingCoverageOut(BaseModel):
    completed_categories: list[str] = Field(default_factory=list)
    missing_categories: list[str] = Field(default_factory=list)
    total_categories: int
    completion_percent: int
    user_items: int = 0
    learned_items: int = 0
    last_learned_at: datetime | None = None


class UserUnderstandingSyncOut(BaseModel):
    created: int = 0
    coverage: UserUnderstandingCoverageOut


class UnderstandingFactOut(BaseModel):
    category: str
    section: str
    field: str
    title: str
    value: str
    confidence: float = Field(default=0.65, ge=0, le=1)
    source: str = "learned"
    evidence: list[str] = Field(default_factory=list)


class UnderstandingInsightOut(BaseModel):
    type: str
    title: str
    description: str
    confidence: float = Field(default=0.65, ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    action: str | None = None


class UnderstandingModelOut(BaseModel):
    identity: dict = Field(default_factory=dict)
    personalLife: dict = Field(default_factory=dict)
    professionalLife: dict = Field(default_factory=dict)
    goals: dict = Field(default_factory=dict)
    relationships: dict = Field(default_factory=dict)
    currentState: dict = Field(default_factory=dict)
    intelligence: dict = Field(default_factory=dict)


class UserUnderstandingEngineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    userId: UUID
    personal: dict = Field(default_factory=dict)
    professional: dict = Field(default_factory=dict)
    goals: dict = Field(default_factory=dict)
    preferences: dict = Field(default_factory=dict)
    learning: dict = Field(default_factory=dict)
    currentFocus: dict = Field(default_factory=dict)
    understandingModel: UnderstandingModelOut = Field(default_factory=UnderstandingModelOut)
    summary: dict = Field(default_factory=dict)
    coverage: UserUnderstandingCoverageOut
    insights: list[UnderstandingInsightOut] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime


class UserUnderstandingRefreshOut(BaseModel):
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    extracted: int = 0
    coverage: UserUnderstandingCoverageOut
    insights: list[UnderstandingInsightOut] = Field(default_factory=list)
    understanding: UserUnderstandingEngineOut

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel
from app.schemas.user_understanding import UserUnderstandingOut


class LearningObservationOut(ORMModel):
    id: UUID
    user_id: UUID
    source_type: str
    source_id: UUID
    signal: str
    created_at: datetime


class LearningSuggestionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=2000)


class LearningEvidenceOut(BaseModel):
    source: str
    count: int


class LearningSuggestionOut(ORMModel):
    id: UUID
    user_id: UUID
    title: str
    description: str
    confidence: float
    status: Literal["pending", "accepted", "ignored", "edited"]
    created_at: datetime
    evidence: list[LearningEvidenceOut] = Field(default_factory=list)


class LearningSettingsUpdate(BaseModel):
    enabled: bool | None = None
    paused: bool | None = None


class LearningSettingsOut(BaseModel):
    enabled: bool
    paused: bool


class LearningEngineOut(BaseModel):
    observations: list[LearningObservationOut] = Field(default_factory=list)
    suggestions: list[LearningSuggestionOut] = Field(default_factory=list)
    approved_understanding: list[UserUnderstandingOut] = Field(default_factory=list)
    settings: LearningSettingsOut

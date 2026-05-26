from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class FeedbackCreate(BaseModel):
    feedback_type: str = Field(pattern="^(issue|suggestion|response_rating|memory_issue|bug|support)$")
    message: str | None = Field(default=None, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)
    conversation_id: UUID | None = None
    message_id: UUID | None = None
    memory_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class FeedbackOut(ORMModel):
    id: UUID
    feedback_type: str
    message: str | None
    rating: int | None
    status: str
    created_at: datetime


class UsageEventCreate(BaseModel):
    event_type: str = Field(max_length=80)
    surface: str | None = Field(default=None, max_length=80)
    value: int | None = None
    metadata: dict = Field(default_factory=dict)


class MemoryFeedbackCreate(BaseModel):
    memory_id: UUID | None = None
    signal: str = Field(pattern="^(relevant|not_relevant|incorrect|missing_context|useful|not_useful|edited|removed)$")
    rating: int | None = Field(default=None, ge=1, le=5)
    corrected_context: str | None = Field(default=None, max_length=4000)
    metadata: dict = Field(default_factory=dict)


class UsefulnessMetrics(BaseModel):
    daily_active_days: int
    conversations_started: int
    messages_sent: int
    memory_events: int
    project_events: int
    task_events: int
    onboarding_events: int
    dashboard_returns: int = 0
    continuation_cards_opened: int = 0
    restoration_actions: int = 0
    feedback_items: int
    average_response_rating: float | None

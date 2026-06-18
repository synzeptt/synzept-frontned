from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class FeedbackCreate(BaseModel):
    feedback_type: str = Field(pattern="^(issue|suggestion|feature_request|improvement|general|response_rating|memory_issue|bug|support|user_interview)$")
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
    metadata_: dict = Field(default_factory=dict, alias="metadata")
    created_at: datetime


class FeedbackSignal(BaseModel):
    id: UUID | None = None
    title: str
    detail: str
    category: str
    feedback_type: str
    sentiment: str
    status: str
    votes: int = 0
    demand_score: int = 0
    created_at: datetime | None = None


class FeedbackCategoryCount(BaseModel):
    category: str
    count: int


class FeedbackIntelligenceOut(BaseModel):
    total: int
    user_sentiment: str
    sentiment_score: int
    categories: list[FeedbackCategoryCount] = Field(default_factory=list)
    most_requested_features: list[FeedbackSignal] = Field(default_factory=list)
    most_common_frustrations: list[FeedbackSignal] = Field(default_factory=list)
    most_common_compliments: list[FeedbackSignal] = Field(default_factory=list)
    emerging_trends: list[FeedbackSignal] = Field(default_factory=list)
    top_reported_issues: list[FeedbackSignal] = Field(default_factory=list)
    product_insights: dict = Field(default_factory=dict)


class FeatureRequestOut(BaseModel):
    id: UUID
    title: str
    detail: str
    category: str
    status: str
    votes: int = 0
    user_voted: bool = False
    demand_score: int = 0
    created_at: datetime


class FeedbackStatusUpdate(BaseModel):
    status: str = Field(pattern="^(new|planned|in_progress|shipped|closed)$")


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

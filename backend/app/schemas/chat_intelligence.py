from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.dashboard import ReturnChangeOut, ReturnOpenLoopOut, ReturnRecommendationOut, ReturnContextOut
from app.schemas.user_understanding import UserUnderstandingProfileOut


class ChatContextRequest(BaseModel):
    conversation_id: UUID | None = None
    project_id: UUID | None = None


class ChatContinueRequest(BaseModel):
    conversation_id: UUID | None = None
    project_id: UUID | None = None


class ChatHistorySummaryOut(BaseModel):
    conversation_id: UUID
    title: str | None = None
    summary: str | None = None
    active_intent: str | None = None
    project_id: UUID | None = None
    updated_at: datetime | None = None


class ChatContextOut(BaseModel):
    who_the_user_is: UserUnderstandingProfileOut
    current_mission: str = ""
    current_focus: str = ""
    active_projects: list[ReturnContextOut] = Field(default_factory=list)
    open_loops: list[ReturnOpenLoopOut] = Field(default_factory=list)
    recent_progress: list[ReturnChangeOut] = Field(default_factory=list)
    recent_decisions: list[ReturnChangeOut] = Field(default_factory=list)
    suggested_next_actions: list[ReturnRecommendationOut] = Field(default_factory=list)

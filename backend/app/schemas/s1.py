from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.continue_context import ContinueContextOut
from app.schemas.daily_brief_phase8 import DailyBriefOut
from app.schemas.user_understanding import UserUnderstandingProfileOut


class S1ContextItem(BaseModel):
    id: str | None = None
    title: str
    detail: str = ""
    href: str | None = None
    priority: str = "medium"
    source: str = "workspace"


class S1RecommendedAction(BaseModel):
    title: str
    reason: str = ""
    href: str = "/chat"


class S1HomeContext(BaseModel):
    greeting: str = "Welcome back"
    mission: str
    focus: str
    last_time: list[S1ContextItem] = Field(default_factory=list)
    open_loops: list[S1ContextItem] = Field(default_factory=list)
    suggested_next_action: S1RecommendedAction
    is_returning: bool = False
    days_since_last_seen: int | None = None


class S1ContextOut(BaseModel):
    version: str = "s1"
    generated_at: datetime
    home: S1HomeContext
    continue_context: ContinueContextOut
    daily_brief: DailyBriefOut
    knows_you: UserUnderstandingProfileOut
    context_sources: dict[str, int] = Field(default_factory=dict)
    capabilities: dict[str, Any] = Field(default_factory=dict)


class S1HomeOut(BaseModel):
    generated_at: datetime
    home: S1HomeContext
    continue_prompt: str
    context_sources: dict[str, int] = Field(default_factory=dict)

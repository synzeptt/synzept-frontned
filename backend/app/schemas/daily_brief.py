from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import ORMModel


class BriefProgressItem(BaseModel):
    type: str
    title: str
    detail: str | None = None


class BriefContext(BaseModel):
    what_matters: list[str] = Field(default_factory=list)
    recent_progress: list[BriefProgressItem] = Field(default_factory=list)
    focus_topics: list[str] = Field(default_factory=list)
    communication_style: str | None = None


class DailyBriefOut(ORMModel):
    id: UUID
    user_id: UUID
    brief_date: date
    summary: str
    open_loops: list[str] = Field(default_factory=list)
    next_step: str
    context: BriefContext
    created_at: datetime

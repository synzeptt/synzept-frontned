from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.chat import ConversationOut
from app.schemas.daily import DailyExperienceOut, DailySuggestion
from app.schemas.memory import MemoryOut
from app.schemas.note import NoteOut
from app.schemas.project import ProjectOut
from app.schemas.task import TaskOut


class RecentActivityOut(BaseModel):
    id: UUID
    type: str
    title: str
    description: str | None = None
    project_id: UUID | None = None
    occurred_at: datetime


class ContinuityCardOut(BaseModel):
    id: str
    type: str
    title: str
    description: str
    action_label: str
    href: str
    continuation_prompt: str = ""
    reason: str = ""
    continuity_score: float = 0.0
    project_id: UUID | None = None
    task_id: UUID | None = None
    conversation_id: UUID | None = None
    priority: str = "medium"
    updated_at: datetime | None = None


class ContinuityThemeOut(BaseModel):
    label: str
    summary: str
    score: float = 0.0
    count: int = 0
    href: str | None = None


class ContinuityTimelineOut(BaseModel):
    date: date
    headline: str
    summary: str
    recurring_priorities: list[str] = Field(default_factory=list)
    recurring_themes: list[str] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)
    continuity_score: float = 0.0


class DashboardStatsOut(BaseModel):
    active_projects: int = 0
    open_tasks: int = 0
    recent_conversations: int = 0
    notes_updated: int = 0


class RetentionSignalOut(BaseModel):
    type: str
    label: str
    description: str
    score: float = 0.0
    href: str | None = None


class ReturningUserOut(BaseModel):
    is_returning: bool = False
    days_since_last_seen: int | None = None
    summary: str = ""
    prompt: str = ""
    signals: list[RetentionSignalOut] = Field(default_factory=list)


class DashboardOut(BaseModel):
    projects: list[ProjectOut]
    recent_conversations: list[ConversationOut] = Field(default_factory=list)
    tasks: list[TaskOut]
    unfinished_tasks: list[TaskOut] = Field(default_factory=list)
    notes: list[NoteOut]
    memories: list[MemoryOut]
    priorities: list[TaskOut]
    recent_activity: list[RecentActivityOut] = Field(default_factory=list)
    continuity_cards: list[ContinuityCardOut] = Field(default_factory=list)
    continuity_summary: str = ""
    recurring_priorities: list[ContinuityThemeOut] = Field(default_factory=list)
    ongoing_themes: list[ContinuityThemeOut] = Field(default_factory=list)
    continuity_timeline: list[ContinuityTimelineOut] = Field(default_factory=list)
    memory_evolution: list[str] = Field(default_factory=list)
    returning_user: ReturningUserOut = Field(default_factory=ReturningUserOut)
    stats: DashboardStatsOut = Field(default_factory=DashboardStatsOut)
    briefing: str
    daily: DailyExperienceOut | None = None
    morning_briefing: str = ""
    evening_summary: str | None = None
    focus_areas: list[str] = Field(default_factory=list)
    suggestions: list[DailySuggestion] = Field(default_factory=list)

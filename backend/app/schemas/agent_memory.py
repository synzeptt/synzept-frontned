from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AgentMemoryItemOut(BaseModel):
    id: str
    type: str
    title: str
    detail: str = ""
    happened_at: datetime
    why_it_mattered: str
    project_id: UUID | None = None
    goal_id: UUID | None = None
    task_id: UUID | None = None
    note_id: UUID | None = None


class AgentMemoryTimelineOut(BaseModel):
    items: list[AgentMemoryItemOut] = Field(default_factory=list)
    what_changed: list[str] = Field(default_factory=list)
    unfinished: list[str] = Field(default_factory=list)
    recommended_next_step: str
    incomplete_goals: list[str] = Field(default_factory=list)
    important_decisions: list[str] = Field(default_factory=list)
    recall_prompts: list[str] = Field(default_factory=list)

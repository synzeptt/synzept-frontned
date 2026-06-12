from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.base import ORMModel
from app.schemas.task import TaskOut

GOAL_STATUSES = {"active", "completed", "paused"}
MILESTONE_STATUSES = {"pending", "in_progress", "completed"}


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    project_id: UUID | None = None


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = None
    project_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in GOAL_STATUSES:
            raise ValueError("status must be active, completed, or paused")
        return value


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=4000)
    position: int | None = Field(default=None, ge=0)


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=4000)
    status: str | None = None
    position: int | None = Field(default=None, ge=0)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in MILESTONE_STATUSES:
            raise ValueError("status must be pending, in_progress, or completed")
        return value


class MilestoneOut(ORMModel):
    id: UUID
    goal_id: UUID
    title: str
    description: str
    status: str
    progress: float
    position: int
    tasks: list[TaskOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GoalOut(ORMModel):
    id: UUID
    user_id: UUID
    project_id: UUID | None
    title: str
    description: str
    status: str
    progress: float
    milestones: list[MilestoneOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class NextActionOut(BaseModel):
    task_id: UUID | None = None
    milestone_id: UUID | None = None
    goal_id: UUID | None = None
    goal_title: str
    milestone_title: str | None = None
    title: str
    reason: str
    priority: str = "medium"


class WeeklyReviewOut(BaseModel):
    period_start: datetime
    period_end: datetime
    completed: list[str] = Field(default_factory=list)
    blocked: list[str] = Field(default_factory=list)
    next_actions: list[NextActionOut] = Field(default_factory=list)


class GoalDashboardOut(BaseModel):
    active_goals: list[GoalOut] = Field(default_factory=list)
    active_projects: list[str] = Field(default_factory=list)
    upcoming_tasks: list[TaskOut] = Field(default_factory=list)
    recommendations: list[NextActionOut] = Field(default_factory=list)

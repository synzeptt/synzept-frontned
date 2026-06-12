from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class IntelligenceItemOut(BaseModel):
    type: str
    title: str
    detail: str
    severity: str = "info"
    priority: str = "medium"
    project_id: UUID | None = None
    goal_id: UUID | None = None
    milestone_id: UUID | None = None
    task_id: UUID | None = None


class ProjectHealthOut(BaseModel):
    project_id: UUID
    project_title: str
    health_score: float
    momentum_score: float
    completion_score: float
    risk_score: float
    reasons: list[str] = Field(default_factory=list)


class FocusOut(BaseModel):
    project_id: UUID | None = None
    project_title: str | None = None
    goal_id: UUID | None = None
    goal_title: str | None = None
    highest_impact_action: IntelligenceItemOut | None = None
    attention_warning: str | None = None


class DailyPlanOut(BaseModel):
    generated_at: datetime
    top_priorities: list[IntelligenceItemOut] = Field(default_factory=list)
    suggested_tasks: list[IntelligenceItemOut] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)


class ProactiveWeeklyReviewOut(BaseModel):
    period_start: datetime
    period_end: datetime
    wins: list[str] = Field(default_factory=list)
    progress_made: list[str] = Field(default_factory=list)
    missed_objectives: list[str] = Field(default_factory=list)
    suggested_next_steps: list[IntelligenceItemOut] = Field(default_factory=list)


class ProactiveOverviewOut(BaseModel):
    daily_plan: DailyPlanOut
    focus: FocusOut
    insights: list[IntelligenceItemOut] = Field(default_factory=list)
    project_health: list[ProjectHealthOut] = Field(default_factory=list)
    recommendations: list[IntelligenceItemOut] = Field(default_factory=list)

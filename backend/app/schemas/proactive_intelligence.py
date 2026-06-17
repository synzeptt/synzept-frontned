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


class ExecutiveBriefOut(BaseModel):
    generated_at: datetime
    what_changed: list[str] = Field(default_factory=list)
    what_matters_now: list[str] = Field(default_factory=list)
    needs_attention: list[IntelligenceItemOut] = Field(default_factory=list)
    recommended_next_action: IntelligenceItemOut | None = None


class MomentumScoreOut(BaseModel):
    score: float
    trend: str
    activity_score: float
    progress_score: float
    consistency_score: float
    explanation: str


class CommitmentOut(BaseModel):
    id: UUID
    title: str
    detail: str = ""
    status: str
    due_at: datetime | None = None
    project_id: UUID | None = None
    goal_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class FounderReportOut(BaseModel):
    period_start: datetime
    period_end: datetime
    growth: list[str] = Field(default_factory=list)
    revenue: list[str] = Field(default_factory=list)
    customers: list[str] = Field(default_factory=list)
    retention: list[str] = Field(default_factory=list)
    product_progress: list[str] = Field(default_factory=list)
    recommendations: list[IntelligenceItemOut] = Field(default_factory=list)


class ChiefOfStaffOut(BaseModel):
    executive_brief: ExecutiveBriefOut
    opportunities: list[IntelligenceItemOut] = Field(default_factory=list)
    risks: list[IntelligenceItemOut] = Field(default_factory=list)
    priorities: list[IntelligenceItemOut] = Field(default_factory=list)
    commitments: list[CommitmentOut] = Field(default_factory=list)
    momentum: MomentumScoreOut
    strategic_suggestions: list[IntelligenceItemOut] = Field(default_factory=list)
    founder_report: FounderReportOut | None = None


class ProactiveOverviewOut(BaseModel):
    daily_plan: DailyPlanOut
    focus: FocusOut
    insights: list[IntelligenceItemOut] = Field(default_factory=list)
    project_health: list[ProjectHealthOut] = Field(default_factory=list)
    recommendations: list[IntelligenceItemOut] = Field(default_factory=list)
    chief_of_staff: ChiefOfStaffOut | None = None

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.proactive_intelligence import IntelligenceItemOut, ProjectHealthOut
from app.schemas.goal import GoalOut


class GoalPlanRequest(BaseModel):
    goal_id: UUID
    create_structure: bool = True


class ExecutionPlanOut(BaseModel):
    id: UUID
    goal_id: UUID
    project_id: UUID | None = None
    status: str
    plan: dict = Field(default_factory=dict)
    planned: list[dict] = Field(default_factory=list)
    completed: list[dict] = Field(default_factory=list)
    blocked: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class GoalPlanOut(BaseModel):
    goal: GoalOut
    execution_plan: ExecutionPlanOut
    milestones_created: int = 0
    tasks_created: int = 0
    open_loops_created: int = 0
    suggested_actions: list[IntelligenceItemOut] = Field(default_factory=list)


class ExecutionStateOut(BaseModel):
    planned: list[dict] = Field(default_factory=list)
    completed: list[dict] = Field(default_factory=list)
    blocked: list[dict] = Field(default_factory=list)


class GoalProgressEstimateOut(BaseModel):
    goal_id: UUID
    current_progress: float
    remaining_work: list[str] = Field(default_factory=list)
    estimated_completion_days: int | None = None
    estimated_completion_label: str


class WeeklyPlanOut(BaseModel):
    generated_at: datetime
    this_week: list[IntelligenceItemOut] = Field(default_factory=list)
    next_week: list[IntelligenceItemOut] = Field(default_factory=list)
    priority_focus: str = ""


class AutonomousSuggestionOut(BaseModel):
    id: UUID
    suggestion_type: str
    title: str
    detail: str
    priority: str
    status: str
    project_id: UUID | None = None
    goal_id: UUID | None = None
    evidence: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AutonomousWorkspaceOut(BaseModel):
    plans: list[ExecutionPlanOut] = Field(default_factory=list)
    project_health: list[ProjectHealthOut] = Field(default_factory=list)
    execution: ExecutionStateOut
    weekly_plan: WeeklyPlanOut
    suggestions: list[AutonomousSuggestionOut] = Field(default_factory=list)

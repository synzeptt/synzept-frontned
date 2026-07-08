from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import TokenResponse


class OnboardingContextIn(BaseModel):
    """Step 2 - minimal high-value context."""

    display_name: str = Field(min_length=1, max_length=120)
    primary_role: str | None = Field(default=None, max_length=120)
    goals: list[str] = Field(default_factory=list)
    current_priorities: list[str] = Field(default_factory=list)
    communication_style: Literal["concise", "balanced", "deep"] = "balanced"
    work_type: str | None = Field(default=None, max_length=80)
    productivity_style: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("goals", "current_priorities")
    @classmethod
    def trim_lists(cls, value: list[str]) -> list[str]:
        return [v.strip() for v in value if v and v.strip()][:5]


class OnboardingWorkspaceIn(BaseModel):
    create_project: bool = False
    project_name: str | None = Field(default=None, max_length=200)
    project_description: str | None = Field(default=None, max_length=1000)
    first_goal: str | None = Field(default=None, max_length=300)
    first_task: str | None = Field(default=None, max_length=300)
    first_note: str | None = Field(default=None, max_length=2000)
    skipped: bool = False


class FirstRunIntelligenceIn(BaseModel):
    building: str = Field(min_length=1, max_length=500)
    top_goals: list[str] = Field(default_factory=list)
    current_focus: str = Field(min_length=1, max_length=500)
    important_projects: list[str] = Field(default_factory=list)
    success_90_days: str = Field(min_length=1, max_length=1000)
    struggling_with: str | None = Field(default=None, max_length=1000)
    help_continue: str | None = Field(default=None, max_length=1000)
    generated_current_mission: str | None = Field(default=None, max_length=1000)
    generated_open_loops: list[str] = Field(default_factory=list)
    generated_suggested_actions: list[str] = Field(default_factory=list)

    @field_validator("top_goals", "important_projects", "generated_open_loops", "generated_suggested_actions")
    @classmethod
    def trim_first_run_lists(cls, value: list[str]) -> list[str]:
        return [v.strip() for v in value if v and v.strip()][:5]


class OnboardingFirstChatIn(BaseModel):
    message: str | None = Field(default=None, max_length=4000)
    use_suggested_prompt: bool = True


class OnboardingDashboardPreview(BaseModel):
    suggested_priorities: list[str] = Field(default_factory=list)
    starter_structure: list[str] = Field(default_factory=list)
    continuity_summary: str = ""
    next_actions: list[str] = Field(default_factory=list)


class OnboardingAnalyticsSummary(BaseModel):
    completed: bool = False
    drop_off_step: str | None = None
    first_ai_interaction_success: bool = False
    first_project_created: bool = False
    first_memory_initialized: bool = False
    day_1_activation: bool = False
    day_7_retention: bool = False
    daily_brief_opens: int = 0
    open_loop_completions: int = 0
    events_tracked: int = 0


class OnboardingStatusOut(BaseModel):
    state: str
    is_complete: bool
    display_name: str | None = None
    goals: list[str] = Field(default_factory=list)
    has_memories: bool = False
    has_workspace: bool = False
    conversation_id: UUID | None = None
    completed_steps: list[str] = Field(default_factory=list)
    skipped_steps: list[str] = Field(default_factory=list)
    initialized_systems: list[str] = Field(default_factory=list)
    resume_step: str = "welcome"
    dashboard_preview: OnboardingDashboardPreview = Field(default_factory=OnboardingDashboardPreview)
    analytics: OnboardingAnalyticsSummary = Field(default_factory=OnboardingAnalyticsSummary)


class OnboardingCompleteOut(BaseModel):
    state: str = "complete"
    project_id: UUID | None = None
    tasks_created: int = 0
    memories_created: int = 0
    conversation_id: UUID | None = None
    welcome_message: str = ""
    welcome_brief: dict = Field(default_factory=dict)
    dashboard_preview: OnboardingDashboardPreview = Field(default_factory=OnboardingDashboardPreview)
    analytics: OnboardingAnalyticsSummary = Field(default_factory=OnboardingAnalyticsSummary)


class OnboardingFirstChatOut(BaseModel):
    conversation_id: UUID
    reply: str
    suggestions: list[dict] = Field(default_factory=list)


class GoogleAuthIn(BaseModel):
    id_token: str = Field(min_length=10)


class AuthResponse(TokenResponse):
    onboarding_state: str
    display_name: str | None = None

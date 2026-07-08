from pydantic import BaseModel, Field


class OnboardingWowStartOut(BaseModel):
    step: str
    title: str
    description: str
    progress: int
    nextLabel: str


class OnboardingWowAdvanceIn(BaseModel):
    focus_area: str | None = None
    goal: str | None = None
    notes: str | None = None


class OnboardingWowAdvanceOut(BaseModel):
    step: str
    progress: int
    mission: str
    missionWhy: str
    dailyOs: str
    actionCenter: list[str] = Field(default_factory=list)
    lifeGraphPreview: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    nextAction: str
    summary: str
    requiresApproval: bool = False

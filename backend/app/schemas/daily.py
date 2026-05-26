from pydantic import BaseModel, Field


class DailySuggestion(BaseModel):
    type: str
    label: str
    description: str


class DailyExperienceOut(BaseModel):
    date: str
    morning_briefing: str
    evening_summary: str | None = None
    briefing: str
    workflow_phase: str = "morning"
    rhythm_prompt: str = ""
    focus_areas: list[str] = Field(default_factory=list)
    suggestions: list[DailySuggestion] = Field(default_factory=list)
    completed_today: list[str] = Field(default_factory=list)
    carry_forward: list[str] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
    tomorrow_priorities: list[str] = Field(default_factory=list)
    continuation_points: list[str] = Field(default_factory=list)
    has_evening: bool = False


class DailyWrapUpIn(BaseModel):
    progress_summary: str | None = Field(default=None, max_length=1200)
    completed: list[str] = Field(default_factory=list, max_length=8)
    unfinished: list[str] = Field(default_factory=list, max_length=8)
    insights: list[str] = Field(default_factory=list, max_length=6)
    tomorrow_priorities: list[str] = Field(default_factory=list, max_length=6)
    continuation_points: list[str] = Field(default_factory=list, max_length=6)

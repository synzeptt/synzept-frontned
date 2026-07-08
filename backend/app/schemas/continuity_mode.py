from pydantic import BaseModel, Field


class ContinuityActionOut(BaseModel):
    label: str
    prompt: str
    mode: str
    project_id: str | None = None


class ContinuityModeOut(BaseModel):
    headline: str
    last_focus: str
    what_changed: list[str] = Field(default_factory=list)
    open_loops: list[str] = Field(default_factory=list)
    recommended_next_action: str
    recommended_reason: str = ""
    actions: list[ContinuityActionOut] = Field(default_factory=list)
    memory_context: list[str] = Field(default_factory=list)
    context_used: dict[str, int] = Field(default_factory=dict)

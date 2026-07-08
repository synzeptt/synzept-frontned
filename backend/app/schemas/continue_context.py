from pydantic import BaseModel, Field


class ContinueContextCardOut(BaseModel):
    id: str
    kind: str
    title: str
    last_activity: str = "No recent activity yet"
    current_status: str = "Ready to continue"
    continue_label: str = "Continue"
    href: str = "/chat"
    project_id: str | None = None
    prompt: str


class ContinueContextOut(BaseModel):
    headline: str = "Welcome back."
    summary: str = ""
    last_activity: list[str] = Field(default_factory=list)
    open_loops: list[str] = Field(default_factory=list)
    suggested_next_action: str = "Choose one meaningful priority for today."
    cards: list[ContinueContextCardOut] = Field(default_factory=list)
    context_used: dict[str, int] = Field(default_factory=dict)

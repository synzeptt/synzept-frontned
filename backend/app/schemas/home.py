from datetime import datetime

from pydantic import BaseModel, Field


class HomeSignalOut(BaseModel):
    id: str | None = None
    title: str
    detail: str = ""
    href: str | None = None
    source: str = "workspace"
    priority: str = "medium"


class HomeActionOut(BaseModel):
    title: str
    reason: str = ""
    href: str = "/chat"
    source: str = "recommendation_engine"


class HomeContinueContextOut(BaseModel):
    title: str = "Continue Working"
    summary: str = ""
    prompt: str = ""
    cards: list[HomeSignalOut] = Field(default_factory=list)
    sources: dict[str, int] = Field(default_factory=dict)


class HomeOut(BaseModel):
    mission: str
    focus: str
    open_loops: list[HomeSignalOut] = Field(default_factory=list)
    suggested_action: HomeActionOut
    continue_context: HomeContinueContextOut
    generated_at: datetime
    empty_state: bool = False
    source_counts: dict[str, int] = Field(default_factory=dict)

from pydantic import BaseModel, Field


class MemoryFeedFactorOut(BaseModel):
    label: str
    value: int = Field(ge=0, le=100)


class MemoryFeedCardOut(BaseModel):
    id: str
    type: str
    title: str
    summary: str
    detail: str
    source: str
    timestamp: str
    dueAt: str | None = None
    relatedPerson: str | None = None
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    factors: list[MemoryFeedFactorOut] = Field(default_factory=list)
    score: float | None = None
    pinned: bool = False
    status: str = "active"
    suggestedAction: str | None = None
    followUpPrompt: str | None = None


class MemoryFeedOut(BaseModel):
    generatedAt: str
    nextRefreshAt: str
    refreshLabel: str
    cards: list[MemoryFeedCardOut] = Field(default_factory=list)

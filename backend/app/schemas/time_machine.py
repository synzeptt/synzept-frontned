from pydantic import BaseModel, Field


class TimeMachineTimelineEntryOut(BaseModel):
    id: str
    kind: str
    title: str
    date: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    magnitude: str
    confidence: float
    context: str
    outcome: str


class TimeMachineTurningPointOut(BaseModel):
    id: str
    title: str
    date: str
    impact: str
    whyItMatters: str
    confidence: float


class TimeMachineReflectionOut(BaseModel):
    id: str
    insight: str
    evidence: list[str] = Field(default_factory=list)
    whyItMatters: str
    confidence: float


class TimeMachineComparisonOut(BaseModel):
    id: str
    label: str
    before: str
    after: str
    changes: list[str] = Field(default_factory=list)


class TimeMachineSearchResultOut(BaseModel):
    id: str
    title: str
    kind: str
    date: str
    snippet: str

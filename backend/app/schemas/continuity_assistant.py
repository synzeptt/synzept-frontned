from pydantic import BaseModel, Field


class AssistantRecommendationOut(BaseModel):
    title: str
    detail: str
    reason: str


class EvidenceCountOut(BaseModel):
    source: str
    count: int


class ExplainedPatternOut(BaseModel):
    title: str
    explanation: str
    confidence: float
    evidence: list[EvidenceCountOut] = Field(default_factory=list)


class ProjectRiskOut(BaseModel):
    project_id: str
    project_title: str
    risk: str
    reasons: list[str] = Field(default_factory=list)


class TurningPointOut(BaseModel):
    event_type: str
    title: str
    description: str
    event_date: str


class HiddenConnectionOut(BaseModel):
    title: str
    detail: str
    node_titles: list[str] = Field(default_factory=list)


class ContinuityAssistantOut(BaseModel):
    greeting: str
    summary: str
    priorities: list[str] = Field(default_factory=list)
    open_loops: list[str] = Field(default_factory=list)
    recent_progress: list[str] = Field(default_factory=list)
    key_context: list[str] = Field(default_factory=list)
    recommendation: AssistantRecommendationOut
    learned_patterns: list[ExplainedPatternOut] = Field(default_factory=list)
    project_risks: list[ProjectRiskOut] = Field(default_factory=list)
    turning_points: list[TurningPointOut] = Field(default_factory=list)
    hidden_connections: list[HiddenConnectionOut] = Field(default_factory=list)

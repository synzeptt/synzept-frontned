from pydantic import BaseModel, Field


class OpportunityOut(BaseModel):
    id: str
    title: str
    category: str
    summary: str
    impact: str
    effort: str
    urgency: str
    confidence: str
    score: int
    expectedOutcome: str
    suggestedFirstAction: str
    evidence: list[str] = Field(default_factory=list)
    source: str


class OpportunityFeedbackOut(BaseModel):
    opportunityId: str
    action: str
    note: str | None = None


class OpportunityScoreBreakdownOut(BaseModel):
    opportunityId: str
    impactScore: int
    confidenceScore: int
    urgencyScore: int
    totalScore: int

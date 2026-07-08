from pydantic import BaseModel, Field


class TrustEvidenceOut(BaseModel):
    id: str
    sourceType: str
    title: str
    detail: str
    link: str | None = None


class TrustRecommendationOut(BaseModel):
    id: str
    recommendation: str
    why: str
    basedOn: list[str] = Field(default_factory=list)
    confidenceScore: float
    confidenceLevel: str
    confidenceExplanation: str
    supportingEvidence: list[TrustEvidenceOut] = Field(default_factory=list)
    relatedMemories: list[str] = Field(default_factory=list)
    relatedMissions: list[str] = Field(default_factory=list)
    relatedDecisions: list[str] = Field(default_factory=list)
    relatedConversations: list[str] = Field(default_factory=list)
    alternativeOptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    expectedOutcome: str
    assumptions: list[str] = Field(default_factory=list)
    missingInformation: list[str] = Field(default_factory=list)


class TrustFeedbackIn(BaseModel):
    recommendationId: str
    feedbackType: str
    note: str | None = None


class TrustFeedbackOut(BaseModel):
    recommendationId: str
    feedbackType: str
    status: str
    message: str

from pydantic import BaseModel, Field


class DecisionEvidenceOut(BaseModel):
    id: str
    sourceType: str
    sourceTitle: str
    quote: str
    strength: int = Field(ge=0, le=100)


class DecisionDetectionOut(BaseModel):
    id: str
    sourceType: str
    sourceTitle: str
    suggestedTitle: str
    rationale: str
    confidence: float = Field(ge=0, le=1)
    shouldSuggestDecision: bool
    evidence: list[DecisionEvidenceOut] = Field(default_factory=list)


class DecisionRecordOut(BaseModel):
    id: str
    title: str
    description: str
    importance: str
    mission: str
    goal: str
    relatedProjects: list[str] = Field(default_factory=list)
    relatedPeople: list[str] = Field(default_factory=list)
    alternativesConsidered: list[str] = Field(default_factory=list)
    expectedOutcome: str
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    currentStatus: str
    reviewState: str
    decidedAt: str
    reviewDueAt: str
    evidence: list[DecisionEvidenceOut] = Field(default_factory=list)


class DecisionReviewOut(BaseModel):
    id: str
    decisionId: str
    decisionTitle: str
    reviewState: str
    scheduledFor: str
    prompt: str
    recommendedUpdate: str


class DecisionOutcomeAnalysisOut(BaseModel):
    id: str
    decisionId: str
    expectedOutcome: str
    actualOutcome: str
    predictionAccuracy: int = Field(ge=0, le=100)
    lessonsLearned: list[str] = Field(default_factory=list)
    futureEvidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class DecisionDNATraitOut(BaseModel):
    id: str
    category: str
    title: str
    summary: str
    confidence: float = Field(ge=0, le=1)
    supportingEvidence: list[str] = Field(default_factory=list)


class DecisionRecommendationOut(BaseModel):
    id: str
    title: str
    scenario: str
    recommendation: str
    reasoning: str
    relevantDecisionIds: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    expectedImpact: int = Field(ge=0, le=100)


class DecisionAnalyticsOut(BaseModel):
    totalDecisions: int
    pendingReviews: int
    completedReviews: int
    averagePredictionAccuracy: int
    highConfidenceSuccessRate: int
    recurringRiskThemes: list[str] = Field(default_factory=list)


class DecisionIntelligenceOut(BaseModel):
    generatedAt: str
    detectionCandidates: list[DecisionDetectionOut] = Field(default_factory=list)
    decisions: list[DecisionRecordOut] = Field(default_factory=list)
    reviews: list[DecisionReviewOut] = Field(default_factory=list)
    outcomeAnalyses: list[DecisionOutcomeAnalysisOut] = Field(default_factory=list)
    decisionDNA: list[DecisionDNATraitOut] = Field(default_factory=list)
    recommendations: list[DecisionRecommendationOut] = Field(default_factory=list)
    analytics: DecisionAnalyticsOut


class DecisionReviewUpdateIn(BaseModel):
    decisionId: str
    reviewState: str
    actualOutcome: str | None = None
    lessonsLearned: list[str] = Field(default_factory=list)

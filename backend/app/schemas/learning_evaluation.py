from pydantic import BaseModel, Field


class RecommendationOut(BaseModel):
    id: str
    title: str
    recommendation: str
    reasoningPlanId: str
    decisionId: str | None = None
    userId: str
    status: str
    confidence: float
    createdAt: str
    expectedOutcomeAt: str
    tags: list[str] = Field(default_factory=list)


class PredictionOut(BaseModel):
    id: str
    recommendationId: str
    predictedOutcome: str
    probability: float
    measurableSignal: str
    horizonDays: int
    assumptions: list[str] = Field(default_factory=list)


class OutcomeOut(BaseModel):
    id: str
    recommendationId: str
    actualOutcome: str
    success: bool
    occurredAt: str
    evidence: list[str] = Field(default_factory=list)
    userFeedback: str | None = None


class EvaluationOut(BaseModel):
    id: str
    recommendationId: str
    predictionId: str
    outcomeId: str
    predictionAccuracy: float
    recommendationAccepted: bool
    recommendationSuccessful: bool
    timeToOutcomeHours: int
    feedbackScore: float
    summary: str
    createdAt: str


class LessonOut(BaseModel):
    id: str
    evaluationId: str
    title: str
    lesson: str
    appliesTo: list[str] = Field(default_factory=list)
    confidenceDelta: float
    decisionProfileUpdate: str


class ConfidenceHistoryOut(BaseModel):
    id: str
    recommendationId: str
    timestamp: str
    confidence: float
    reason: str


class DecisionProfileOut(BaseModel):
    userId: str
    calibrationScore: float
    strengths: list[str] = Field(default_factory=list)
    blindSpots: list[str] = Field(default_factory=list)
    recommendationPreferences: list[str] = Field(default_factory=list)
    updatedAt: str


class FeedbackIn(BaseModel):
    feedback: str
    note: str | None = None


class RecordRecommendationIn(BaseModel):
    title: str
    recommendation: str
    reasoningPlanId: str
    decisionId: str | None = None
    confidence: float
    predictedOutcome: str
    probability: float
    measurableSignal: str
    horizonDays: int = 7
    tags: list[str] = Field(default_factory=list)


class RecordOutcomeIn(BaseModel):
    actualOutcome: str
    success: bool
    evidence: list[str] = Field(default_factory=list)
    userFeedback: str | None = None


class EvaluationMetricsOut(BaseModel):
    predictionAccuracy: float
    recommendationAcceptanceRate: float
    recommendationSuccessRate: float
    averageTimeToOutcomeHours: float
    userFeedbackScore: float


class LearningEvaluationDashboardOut(BaseModel):
    generatedAt: str
    recommendations: list[RecommendationOut] = Field(default_factory=list)
    predictions: list[PredictionOut] = Field(default_factory=list)
    outcomes: list[OutcomeOut] = Field(default_factory=list)
    evaluations: list[EvaluationOut] = Field(default_factory=list)
    lessons: list[LessonOut] = Field(default_factory=list)
    confidenceHistory: list[ConfidenceHistoryOut] = Field(default_factory=list)
    metrics: EvaluationMetricsOut
    decisionProfile: DecisionProfileOut

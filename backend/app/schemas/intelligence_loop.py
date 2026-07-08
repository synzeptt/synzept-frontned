from pydantic import BaseModel, Field


class EvidenceOut(BaseModel):
    sourceId: str
    sourceType: str
    summary: str
    strength: int = Field(ge=0, le=100)


class IntelligenceEventOut(BaseModel):
    id: str
    source: str
    eventType: str
    title: str
    description: str
    occurredAt: str
    actor: str
    entities: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    importance: int = Field(ge=0, le=100)
    urgency: int = Field(ge=0, le=100)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class UserModelSignalOut(BaseModel):
    id: str
    category: str
    label: str
    value: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceOut] = Field(default_factory=list)
    updatedAt: str


class UserModelOut(BaseModel):
    goals: list[UserModelSignalOut] = Field(default_factory=list)
    priorities: list[UserModelSignalOut] = Field(default_factory=list)
    interests: list[UserModelSignalOut] = Field(default_factory=list)
    relationships: list[UserModelSignalOut] = Field(default_factory=list)
    workingPatterns: list[UserModelSignalOut] = Field(default_factory=list)


class PredictionOut(BaseModel):
    id: str
    kind: str
    title: str
    forecast: str
    probability: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    horizon: str
    supportingEvidence: list[EvidenceOut] = Field(default_factory=list)
    riskLevel: str


class RecommendationOut(BaseModel):
    id: str
    title: str
    action: str
    why: str
    expectedImpact: int = Field(ge=0, le=100)
    effort: str
    confidence: float = Field(ge=0, le=1)
    rankedScore: float
    linkedPredictionIds: list[str] = Field(default_factory=list)
    requiresApproval: bool = True


class ActionRequestOut(BaseModel):
    id: str
    recommendationId: str
    title: str
    description: str
    permissionLevel: str
    status: str
    approvalPrompt: str
    preview: dict[str, str] = Field(default_factory=dict)


class ActionApprovalIn(BaseModel):
    actionRequestId: str
    approved: bool
    note: str | None = None


class LearningOutcomeIn(BaseModel):
    targetId: str
    targetType: str
    outcome: str
    note: str | None = None


class LearningOutcomeOut(BaseModel):
    id: str
    targetId: str
    targetType: str
    outcome: str
    adjustment: str
    recordedAt: str
    note: str | None = None


class IntelligenceLoopSnapshotOut(BaseModel):
    generatedAt: str
    events: list[IntelligenceEventOut] = Field(default_factory=list)
    userModel: UserModelOut
    predictions: list[PredictionOut] = Field(default_factory=list)
    recommendations: list[RecommendationOut] = Field(default_factory=list)
    actionRequests: list[ActionRequestOut] = Field(default_factory=list)
    learningOutcomes: list[LearningOutcomeOut] = Field(default_factory=list)
    loopHealth: dict[str, int | str] = Field(default_factory=dict)

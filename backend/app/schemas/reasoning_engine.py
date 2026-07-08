from pydantic import BaseModel, Field


class ReasoningRequestIn(BaseModel):
    requestId: str
    userId: str = "mock-user"
    message: str
    conversationId: str | None = None
    metadata: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)


class IntentAnalysisOut(BaseModel):
    intent: str
    objective: str
    urgency: str
    confidence: float
    signals: list[str] = Field(default_factory=list)


class RetrievedItemOut(BaseModel):
    id: str
    type: str
    title: str
    summary: str
    relevance: float
    source: str


class EvidenceItemOut(BaseModel):
    id: str
    claim: str
    source: str
    strength: float
    supports: str


class RiskItemOut(BaseModel):
    id: str
    title: str
    severity: str
    likelihood: float
    mitigation: str


class OpportunityItemOut(BaseModel):
    id: str
    title: str
    expectedImpact: float
    rationale: str


class ReasoningPlanOut(BaseModel):
    hasEnoughInformation: bool
    clarificationNeeded: bool
    clarificationQuestion: str | None = None
    relevantMemoryIds: list[str] = Field(default_factory=list)
    similarDecisionIds: list[str] = Field(default_factory=list)
    evidenceIds: list[str] = Field(default_factory=list)
    risksToMention: list[str] = Field(default_factory=list)
    opportunitiesToMention: list[str] = Field(default_factory=list)
    recommendation: str
    responseStrategy: str
    llmInstructions: list[str] = Field(default_factory=list)


class PipelineStepOut(BaseModel):
    name: str
    component: str
    status: str
    summary: str
    confidence: float


class LlmHandoffOut(BaseModel):
    role: str
    structuredContext: dict[str, object]
    reasoningPlan: ReasoningPlanOut
    supportingEvidence: list[EvidenceItemOut] = Field(default_factory=list)
    guardrails: list[str] = Field(default_factory=list)


class ReasoningResponseOut(BaseModel):
    requestId: str
    generatedAt: str
    pipeline: list[PipelineStepOut] = Field(default_factory=list)
    intent: IntentAnalysisOut
    context: list[RetrievedItemOut] = Field(default_factory=list)
    memories: list[RetrievedItemOut] = Field(default_factory=list)
    knowledge: list[RetrievedItemOut] = Field(default_factory=list)
    decisions: list[RetrievedItemOut] = Field(default_factory=list)
    evidence: list[EvidenceItemOut] = Field(default_factory=list)
    risks: list[RiskItemOut] = Field(default_factory=list)
    opportunities: list[OpportunityItemOut] = Field(default_factory=list)
    plan: ReasoningPlanOut
    llmHandoff: LlmHandoffOut
    composedResponse: str

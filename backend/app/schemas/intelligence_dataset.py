from pydantic import BaseModel, Field


class ObjectRelationshipOut(BaseModel):
    type: str
    targetId: str
    confidence: float = 0.75
    evidence: str | None = None


class SynzeptObjectOut(BaseModel):
    id: str
    type: str
    title: str
    summary: str
    confidence: float
    source: str
    createdAt: str
    updatedAt: str
    metadata: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)
    relationships: list[ObjectRelationshipOut] = Field(default_factory=list)


class GoalObjectOut(SynzeptObjectOut):
    type: str = "goal"


class DecisionObjectOut(SynzeptObjectOut):
    type: str = "decision"


class TaskObjectOut(SynzeptObjectOut):
    type: str = "task"


class ConversationExtractIn(BaseModel):
    conversationId: str
    title: str
    transcript: str
    source: str = "conversation"
    metadata: dict[str, str | int | float | bool | list[str]] = Field(default_factory=dict)


class PipelineStageOut(BaseModel):
    name: str
    status: str
    summary: str
    objectCount: int = 0


class ReviewItemOut(BaseModel):
    id: str
    object: SynzeptObjectOut
    status: str
    impact: str
    extractor: str
    rationale: str
    createdAt: str


class ReviewEditIn(BaseModel):
    title: str | None = None
    summary: str | None = None
    confidence: float | None = None
    metadata: dict[str, str | int | float | bool | list[str]] | None = None


class ReviewActionOut(BaseModel):
    status: str
    reviewItem: ReviewItemOut | None = None
    graphNode: SynzeptObjectOut | None = None


class GraphEdgeOut(BaseModel):
    id: str
    sourceId: str
    targetId: str
    type: str
    confidence: float
    evidence: str


class KnowledgeGraphOut(BaseModel):
    nodes: list[SynzeptObjectOut] = Field(default_factory=list)
    edges: list[GraphEdgeOut] = Field(default_factory=list)


class ExtractionResultOut(BaseModel):
    conversationId: str
    stages: list[PipelineStageOut] = Field(default_factory=list)
    pendingReviewItems: list[ReviewItemOut] = Field(default_factory=list)
    graphPreview: KnowledgeGraphOut

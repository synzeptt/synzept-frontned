from pydantic import BaseModel, Field


class DecisionGraphNodeOut(BaseModel):
    id: str
    type: str
    title: str
    description: str
    timestamp: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: str | None = None
    importance: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class DecisionGraphEdgeOut(BaseModel):
    id: str
    source: str
    target: str
    relationship: str
    label: str
    strength: int = Field(ge=0, le=100)
    evidence: list[str] = Field(default_factory=list)


class DecisionGraphInsightOut(BaseModel):
    id: str
    type: str
    title: str
    summary: str
    supportingConnectionIds: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    impact: int = Field(ge=0, le=100)


class DecisionGraphChainOut(BaseModel):
    id: str
    title: str
    nodeIds: list[str] = Field(default_factory=list)
    edgeIds: list[str] = Field(default_factory=list)
    summary: str


class DecisionGraphOut(BaseModel):
    generatedAt: str
    nodes: list[DecisionGraphNodeOut] = Field(default_factory=list)
    edges: list[DecisionGraphEdgeOut] = Field(default_factory=list)
    insights: list[DecisionGraphInsightOut] = Field(default_factory=list)
    chains: list[DecisionGraphChainOut] = Field(default_factory=list)
    supportedRelationships: list[str] = Field(default_factory=list)

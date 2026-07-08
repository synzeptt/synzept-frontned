from pydantic import BaseModel, Field


class LifeGraphEntityOut(BaseModel):
    id: str
    type: str
    title: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class LifeGraphRelationshipOut(BaseModel):
    id: str
    source: str
    target: str
    type: str
    direction: str = "outgoing"
    strength: float = 0.5
    evidence: str


class LifeGraphPathOut(BaseModel):
    nodes: list[LifeGraphEntityOut] = Field(default_factory=list)
    relationships: list[LifeGraphRelationshipOut] = Field(default_factory=list)


class LifeGraphExplorationOut(BaseModel):
    query: str = ""
    entityType: str | None = None
    entities: list[LifeGraphEntityOut] = Field(default_factory=list)
    relationships: list[LifeGraphRelationshipOut] = Field(default_factory=list)
    paths: list[LifeGraphPathOut] = Field(default_factory=list)
    aiInsights: list[str] = Field(default_factory=list)

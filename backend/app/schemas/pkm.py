from pydantic import BaseModel, Field


class PkmAttributeOut(BaseModel):
    value: str
    confidence: int
    evidence: list[str] = Field(default_factory=list)
    lastUpdated: str
    source: str


class PkmDomainOut(BaseModel):
    key: str
    title: str
    attributes: list[PkmAttributeOut] = Field(default_factory=list)


class PkmModelOut(BaseModel):
    userName: str
    summary: str
    domains: list[PkmDomainOut] = Field(default_factory=list)
    learningTimeline: list[str] = Field(default_factory=list)

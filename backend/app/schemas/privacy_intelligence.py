from pydantic import BaseModel, Field


class PrivacyContributionSettingsOut(BaseModel):
    optedIn: bool
    mode: str
    lastUpdatedAt: str
    anonymizationLevel: str
    localOnlySignals: list[str] = Field(default_factory=list)
    sharedAggregateSignals: list[str] = Field(default_factory=list)


class PrivacyContributionSettingsIn(BaseModel):
    optedIn: bool
    mode: str = "anonymous_patterns"


class PersonalEvidenceOut(BaseModel):
    id: str
    type: str
    title: str
    summary: str
    confidence: float = Field(ge=0, le=1)


class GlobalPatternOut(BaseModel):
    id: str
    patternType: str
    title: str
    summary: str
    sampleSize: int = Field(ge=0)
    anonymization: str
    confidence: float = Field(ge=0, le=1)
    outcomeLift: int = Field(ge=-100, le=100)


class PrivacyRecommendationOut(BaseModel):
    id: str
    title: str
    recommendation: str
    personalEvidence: list[PersonalEvidenceOut] = Field(default_factory=list)
    globalPatterns: list[GlobalPatternOut] = Field(default_factory=list)
    reasoning: str
    privacyExplanation: str
    confidence: float = Field(ge=0, le=1)
    expectedImpact: int = Field(ge=0, le=100)


class PrivacyAuditEventOut(BaseModel):
    id: str
    event: str
    description: str
    timestamp: str
    dataBoundary: str


class PrivacyIntelligenceOut(BaseModel):
    generatedAt: str
    architectureLayers: dict[str, list[str]]
    contributionSettings: PrivacyContributionSettingsOut
    recommendations: list[PrivacyRecommendationOut] = Field(default_factory=list)
    globalPatterns: list[GlobalPatternOut] = Field(default_factory=list)
    auditTrail: list[PrivacyAuditEventOut] = Field(default_factory=list)
    privacyGuarantees: list[str] = Field(default_factory=list)

from pydantic import BaseModel, Field


class ScenarioComparisonOut(BaseModel):
    effort: int = Field(ge=0, le=100)
    risk: int = Field(ge=0, le=100)
    cost: int = Field(ge=0, le=100)
    time: int = Field(ge=0, le=100)
    goalAlignment: int = Field(ge=0, le=100)
    expectedImpact: int = Field(ge=0, le=100)


class DecisionScenarioOut(BaseModel):
    id: str
    title: str
    summary: str
    potentialBenefits: list[str] = Field(default_factory=list)
    potentialRisks: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    bestCaseOutcome: str
    worstCaseOutcome: str
    keyUncertainties: list[str] = Field(default_factory=list)
    comparison: ScenarioComparisonOut


class SimulatorInputContextOut(BaseModel):
    decisionId: str
    decisionTitle: str
    personalKnowledgeSignals: list[str] = Field(default_factory=list)
    decisionGraphConnections: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    missions: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    memories: list[str] = Field(default_factory=list)
    riskPreference: str
    pastOutcomeSignals: list[str] = Field(default_factory=list)


class FinalChoiceOut(BaseModel):
    scenarioId: str
    chosenAt: str
    rationale: str
    status: str


class SimulationLearningOut(BaseModel):
    id: str
    scenarioId: str
    predictedResult: str
    actualResult: str
    accuracy: int = Field(ge=0, le=100)
    lessonsLearned: list[str] = Field(default_factory=list)


class DecisionSimulationOut(BaseModel):
    id: str
    generatedAt: str
    inputContext: SimulatorInputContextOut
    scenarios: list[DecisionScenarioOut] = Field(default_factory=list)
    finalChoice: FinalChoiceOut | None = None
    learning: SimulationLearningOut | None = None


class FinalChoiceIn(BaseModel):
    simulationId: str
    scenarioId: str
    rationale: str


class SimulationOutcomeIn(BaseModel):
    simulationId: str
    scenarioId: str
    actualResult: str
    lessonsLearned: list[str] = Field(default_factory=list)

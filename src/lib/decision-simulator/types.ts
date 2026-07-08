export type ScenarioComparison = {
  effort: number;
  risk: number;
  cost: number;
  time: number;
  goalAlignment: number;
  expectedImpact: number;
};

export type DecisionScenario = {
  id: string;
  title: string;
  summary: string;
  potentialBenefits: string[];
  potentialRisks: string[];
  assumptions: string[];
  confidence: number;
  bestCaseOutcome: string;
  worstCaseOutcome: string;
  keyUncertainties: string[];
  comparison: ScenarioComparison;
};

export type SimulatorInputContext = {
  decisionId: string;
  decisionTitle: string;
  personalKnowledgeSignals: string[];
  decisionGraphConnections: string[];
  goals: string[];
  missions: string[];
  projects: string[];
  memories: string[];
  riskPreference: string;
  pastOutcomeSignals: string[];
};

export type FinalChoice = {
  scenarioId: string;
  chosenAt: string;
  rationale: string;
  status: string;
};

export type SimulationLearning = {
  id: string;
  scenarioId: string;
  predictedResult: string;
  actualResult: string;
  accuracy: number;
  lessonsLearned: string[];
};

export type DecisionSimulation = {
  id: string;
  generatedAt: string;
  inputContext: SimulatorInputContext;
  scenarios: DecisionScenario[];
  finalChoice: FinalChoice | null;
  learning: SimulationLearning | null;
};

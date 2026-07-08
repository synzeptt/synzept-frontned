export type PipelineStep = {
  name: string;
  component: string;
  status: string;
  summary: string;
  confidence: number;
};

export type IntentAnalysis = {
  intent: string;
  objective: string;
  urgency: string;
  confidence: number;
  signals: string[];
};

export type RetrievedItem = {
  id: string;
  type: string;
  title: string;
  summary: string;
  relevance: number;
  source: string;
};

export type EvidenceItem = {
  id: string;
  claim: string;
  source: string;
  strength: number;
  supports: string;
};

export type RiskItem = {
  id: string;
  title: string;
  severity: string;
  likelihood: number;
  mitigation: string;
};

export type OpportunityItem = {
  id: string;
  title: string;
  expectedImpact: number;
  rationale: string;
};

export type ReasoningPlan = {
  hasEnoughInformation: boolean;
  clarificationNeeded: boolean;
  clarificationQuestion: string | null;
  relevantMemoryIds: string[];
  similarDecisionIds: string[];
  evidenceIds: string[];
  risksToMention: string[];
  opportunitiesToMention: string[];
  recommendation: string;
  responseStrategy: string;
  llmInstructions: string[];
};

export type LlmHandoff = {
  role: string;
  structuredContext: Record<string, unknown>;
  reasoningPlan: ReasoningPlan;
  supportingEvidence: EvidenceItem[];
  guardrails: string[];
};

export type ReasoningEngineMock = {
  requestId: string;
  generatedAt: string;
  pipeline: PipelineStep[];
  intent: IntentAnalysis;
  context: RetrievedItem[];
  memories: RetrievedItem[];
  knowledge: RetrievedItem[];
  decisions: RetrievedItem[];
  evidence: EvidenceItem[];
  risks: RiskItem[];
  opportunities: OpportunityItem[];
  plan: ReasoningPlan;
  llmHandoff: LlmHandoff;
  composedResponse: string;
};

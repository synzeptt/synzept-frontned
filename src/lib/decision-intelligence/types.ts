export type DecisionEvidence = {
  id: string;
  sourceType: string;
  sourceTitle: string;
  quote: string;
  strength: number;
};

export type DecisionDetection = {
  id: string;
  sourceType: string;
  sourceTitle: string;
  suggestedTitle: string;
  rationale: string;
  confidence: number;
  shouldSuggestDecision: boolean;
  evidence: DecisionEvidence[];
};

export type DecisionRecord = {
  id: string;
  title: string;
  description: string;
  importance: string;
  mission: string;
  goal: string;
  relatedProjects: string[];
  relatedPeople: string[];
  alternativesConsidered: string[];
  expectedOutcome: string;
  risks: string[];
  confidence: number;
  currentStatus: string;
  reviewState: string;
  decidedAt: string;
  reviewDueAt: string;
  evidence: DecisionEvidence[];
};

export type DecisionReview = {
  id: string;
  decisionId: string;
  decisionTitle: string;
  reviewState: string;
  scheduledFor: string;
  prompt: string;
  recommendedUpdate: string;
};

export type DecisionOutcomeAnalysis = {
  id: string;
  decisionId: string;
  expectedOutcome: string;
  actualOutcome: string;
  predictionAccuracy: number;
  lessonsLearned: string[];
  futureEvidence: string[];
  confidence: number;
};

export type DecisionDNATrait = {
  id: string;
  category: string;
  title: string;
  summary: string;
  confidence: number;
  supportingEvidence: string[];
};

export type DecisionRecommendation = {
  id: string;
  title: string;
  scenario: string;
  recommendation: string;
  reasoning: string;
  relevantDecisionIds: string[];
  confidence: number;
  expectedImpact: number;
};

export type DecisionAnalytics = {
  totalDecisions: number;
  pendingReviews: number;
  completedReviews: number;
  averagePredictionAccuracy: number;
  highConfidenceSuccessRate: number;
  recurringRiskThemes: string[];
};

export type DecisionIntelligenceData = {
  generatedAt: string;
  detectionCandidates: DecisionDetection[];
  decisions: DecisionRecord[];
  reviews: DecisionReview[];
  outcomeAnalyses: DecisionOutcomeAnalysis[];
  decisionDNA: DecisionDNATrait[];
  recommendations: DecisionRecommendation[];
  analytics: DecisionAnalytics;
};

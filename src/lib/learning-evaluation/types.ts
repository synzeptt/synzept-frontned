export type Recommendation = {
  id: string;
  title: string;
  recommendation: string;
  reasoningPlanId: string;
  decisionId: string | null;
  status: string;
  confidence: number;
  createdAt: string;
  expectedOutcomeAt: string;
  tags: string[];
};

export type Evaluation = {
  id: string;
  recommendationId: string;
  predictionAccuracy: number;
  recommendationAccepted: boolean;
  recommendationSuccessful: boolean;
  timeToOutcomeHours: number;
  feedbackScore: number;
  summary: string;
  createdAt: string;
};

export type Lesson = {
  id: string;
  evaluationId: string;
  title: string;
  lesson: string;
  appliesTo: string[];
  confidenceDelta: number;
  decisionProfileUpdate: string;
};

export type ConfidencePoint = {
  id: string;
  recommendationId: string;
  timestamp: string;
  confidence: number;
  reason: string;
};

export type EvaluationMetrics = {
  predictionAccuracy: number;
  recommendationAcceptanceRate: number;
  recommendationSuccessRate: number;
  averageTimeToOutcomeHours: number;
  userFeedbackScore: number;
};

export type DecisionProfile = {
  userId: string;
  calibrationScore: number;
  strengths: string[];
  blindSpots: string[];
  recommendationPreferences: string[];
  updatedAt: string;
};

export type LearningEvaluationMock = {
  generatedAt: string;
  recommendations: Recommendation[];
  evaluations: Evaluation[];
  lessons: Lesson[];
  confidenceHistory: ConfidencePoint[];
  metrics: EvaluationMetrics;
  decisionProfile: DecisionProfile;
};

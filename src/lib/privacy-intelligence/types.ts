export type PrivacyContributionSettings = {
  optedIn: boolean;
  mode: string;
  lastUpdatedAt: string;
  anonymizationLevel: string;
  localOnlySignals: string[];
  sharedAggregateSignals: string[];
};

export type PersonalEvidence = {
  id: string;
  type: string;
  title: string;
  summary: string;
  confidence: number;
};

export type GlobalPattern = {
  id: string;
  patternType: string;
  title: string;
  summary: string;
  sampleSize: number;
  anonymization: string;
  confidence: number;
  outcomeLift: number;
};

export type PrivacyRecommendation = {
  id: string;
  title: string;
  recommendation: string;
  personalEvidence: PersonalEvidence[];
  globalPatterns: GlobalPattern[];
  reasoning: string;
  privacyExplanation: string;
  confidence: number;
  expectedImpact: number;
};

export type PrivacyAuditEvent = {
  id: string;
  event: string;
  description: string;
  timestamp: string;
  dataBoundary: string;
};

export type PrivacyIntelligenceData = {
  generatedAt: string;
  architectureLayers: {
    personalIntelligence: string[];
    globalIntelligence: string[];
  };
  contributionSettings: PrivacyContributionSettings;
  recommendations: PrivacyRecommendation[];
  globalPatterns: GlobalPattern[];
  auditTrail: PrivacyAuditEvent[];
  privacyGuarantees: string[];
};

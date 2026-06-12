import type { UserUnderstanding } from "./user-understanding";

export type LearningObservation = {
  id: string;
  user_id: string;
  source_type: string;
  source_id: string;
  signal: string;
  created_at: string;
};

export type LearningSuggestion = {
  id: string;
  user_id: string;
  title: string;
  description: string;
  confidence: number;
  status: "pending" | "accepted" | "ignored" | "edited";
  created_at: string;
  evidence: Array<{ source: string; count: number }>;
};

export type LearningSettings = {
  enabled: boolean;
  paused: boolean;
};

export type LearningEngine = {
  observations: LearningObservation[];
  suggestions: LearningSuggestion[];
  approved_understanding: UserUnderstanding[];
  settings: LearningSettings;
};

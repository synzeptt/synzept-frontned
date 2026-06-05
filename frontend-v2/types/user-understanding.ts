export type UnderstandingSectionKey =
  | "personal"
  | "professional"
  | "goals"
  | "preferences"
  | "learning"
  | "currentFocus";

export type UserUnderstandingProfile = {
  id: string;
  userId: string;
  personal: Record<string, string>;
  professional: Record<string, string>;
  goals: Record<string, string>;
  preferences: Record<string, string>;
  learning: Record<string, string>;
  currentFocus: Record<string, string>;
  createdAt: string;
  updatedAt: string;
};

export type LearningSuggestion = {
  id: string;
  userId: string;
  title: string;
  description: string;
  status: "pending" | "accepted" | "ignored";
  createdAt: string;
  updatedAt: string;
};

export type UnderstandingField = {
  key?: string;
  label?: string;
  title?: string;
  placeholder: string;
  multiline?: boolean;
};

export type UnderstandingSource = "user" | "learned";
export type UnderstandingCategory = "personal" | "professional" | "goals" | "preferences" | "learning" | "currentFocus" | "learned_insights";
export type UserUnderstanding = {
  id: string;
  user_id: string;
  category: UnderstandingCategory;
  title: string;
  value: string;
  source: UnderstandingSource;
  confidence: number | null;
  learned_at: string | null;
  created_at: string;
  updated_at: string;
};

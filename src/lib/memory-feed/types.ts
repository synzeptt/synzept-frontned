export type MemoryFeedCardType =
  | "important_memory"
  | "recent_decision"
  | "open_loop"
  | "mission_progress"
  | "relationship_reminder"
  | "opportunity"
  | "ai_insight"
  | "weekly_reflection"
  | "achievement"
  | "suggested_next_action";

export type MemoryFeedStatus = "active" | "completed" | "snoozed" | "archived";

export type MemoryFeedFactor = {
  label: "Relevance" | "Urgency" | "Importance" | "Recency" | "Feedback";
  value: number;
};

export type MemoryFeedCard = {
  id: string;
  type: MemoryFeedCardType;
  title: string;
  summary: string;
  detail: string;
  source: string;
  timestamp: string;
  dueAt?: string;
  relatedPerson?: string;
  project?: string;
  tags: string[];
  factors: MemoryFeedFactor[];
  score?: number;
  pinned?: boolean;
  status?: MemoryFeedStatus;
  suggestedAction?: string;
  followUpPrompt?: string;
};

export type MemoryFeedResponse = {
  generatedAt: string;
  nextRefreshAt: string;
  refreshLabel: string;
  cards: MemoryFeedCard[];
};

export type MemoryFeedFilter = "all" | MemoryFeedCardType;

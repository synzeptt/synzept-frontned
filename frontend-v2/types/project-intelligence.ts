export type ProjectIntelligenceStatus = "active" | "paused" | "completed";

export type ProjectDecision = {
  id: string;
  project_id: string;
  decision: string;
  status: "open" | "resolved";
  created_at: string;
};

export type ProjectOpenLoop = {
  id: string;
  project_id: string;
  loop: string;
  status: "open" | "closed";
  created_at: string;
};

export type ProjectActivity = {
  id: string;
  type: "conversation" | "note" | "memory" | "task";
  title: string;
  detail: string | null;
  occurred_at: string;
};

export type ProjectIntelligencePage = {
  project_id: string;
  project_name: string;
  project_summary: string;
  status: ProjectIntelligenceStatus;
  last_activity: string;
  current_focus: string;
  recommended_next_step: string;
  recent_activity: ProjectActivity[];
  decisions: ProjectDecision[];
  open_loops: ProjectOpenLoop[];
  conversations: Array<{ id: string; title: string; summary: string | null; updated_at: string }>;
  memories: Array<{ id: string; title: string; content: string; updated_at: string }>;
  risk: { level: "low" | "medium" | "high"; reasons: string[] };
};

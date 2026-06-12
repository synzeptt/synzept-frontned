export type BriefProgressItem = {
  type: "project" | "conversation" | "task" | string;
  title: string;
  detail: string | null;
};

export type DailyBrief = {
  id: string;
  user_id: string;
  brief_date: string;
  summary: string;
  open_loops: string[];
  next_step: string;
  context: {
    what_matters: string[];
    recent_progress: BriefProgressItem[];
    focus_topics: string[];
    communication_style: string | null;
  };
  created_at: string;
};

export type ChatRole = "user" | "assistant" | "system";

export type MemoryCategory =
  | "goal"
  | "preference"
  | "project"
  | "habit"
  | "workflow"
  | "idea"
  | "other";

export type AgentActionType = "task" | "note" | "reminder" | "query" | "none";
export type AgentQueryTopic = "priorities" | "tasks" | "notes" | "memory" | "none";

export interface AgentAction {
  type: AgentActionType;
  title?: string;
  details?: string;
  dueAt?: string;
  priority?: "low" | "medium" | "high";
  queryTopic?: AgentQueryTopic;
}

export interface MemoryRecord {
  id: string;
  content: string;
  category: MemoryCategory;
  created_at: string;
}

export interface TaskRecord {
  id: string;
  title: string;
  description: string | null;
  priority: string | null;
  status: string;
  due_at: string | null;
  created_at: string;
}

export interface NoteRecord {
  id: string;
  title: string | null;
  content: string;
  created_at: string;
}

export interface ReminderRecord {
  id: string;
  content: string;
  remind_at: string | null;
  created_at: string;
}

export interface ChatMessageRow {
  id: string;
  role: ChatRole;
  content: string;
  created_at: string;
}

export interface DashboardData {
  tasks: TaskRecord[];
  notes: NoteRecord[];
  reminders: ReminderRecord[];
  memories: MemoryRecord[];
  messages: ChatMessageRow[];
  priorities: TaskRecord[];
}

export interface MissionProject {
  id: string;
  name: string;
  description: string;
  status: string;
  currentFocus: string;
  recommendedNextStep: string;
}

export interface MissionGoal {
  id: string;
  title: string;
  description: string;
  status: string;
}

export interface MissionOpenLoop {
  id: string;
  title: string;
  description: string;
  projectName: string;
  priority: string;
}

export interface MissionTimelineItem {
  id: string;
  title: string;
  detail: string;
  date: string;
}

export interface MissionInsight {
  id: string;
  title: string;
  detail: string;
  confidence: number;
}

export interface MissionRecommendation {
  id: string;
  title: string;
  detail: string;
  source: string;
}

export interface Mission {
  id: string;
  title: string;
  description: string;
  status: string;
  progress: number;
  startDate: string;
  targetDate: string;
  priority: string;
  healthScore: number;
  momentumScore: number;
  projects: MissionProject[];
  goals: MissionGoal[];
  openLoops: MissionOpenLoop[];
  timeline: MissionTimelineItem[];
  insights: MissionInsight[];
  recommendations: MissionRecommendation[];
}

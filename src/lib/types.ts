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

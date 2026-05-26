import type { Conversation, Note, Project, Task } from "@/lib/api";

export type WorkspaceSection = "dashboard" | "chat" | "projects" | "notes" | "tasks" | "settings";

export type StreamStatus = "idle" | "connecting" | "streaming" | "error";

export type ProjectWorkspace = {
  project: Project;
  conversations: Conversation[];
  notes: Note[];
  tasks: Task[];
};

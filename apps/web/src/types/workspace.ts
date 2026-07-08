export type WorkspacePage =
  | "dashboard"
  | "chat"
  | "projects"
  | "documents"
  | "workflows"
  | "settings";

export type WorkspaceProject = {
  id: string;
  name: string;
  description: string;
  status: "active" | "archived" | "completed";
  tags: string[];
  updatedAt: string;
};

export type WorkspaceDocument = {
  id: string;
  title: string;
  type: "pdf" | "docx" | "txt" | "markdown" | "image";
  summary: string;
  projectId?: string;
  updatedAt: string;
  chunks: number;
};

export type WorkspaceTask = {
  id: string;
  title: string;
  objective: string;
  status: string;
  progress: number;
  updatedAt: string;
};

export type WorkspaceWorkflow = {
  id: string;
  name: string;
  description: string;
  category: string;
  nodes: Array<{ id: string; type: string; label: string; x: number; y: number }>;
  edges: Array<{ id: string; from: string; to: string }>;
};

export type WorkspaceMemory = {
  id: string;
  scope: string;
  title: string;
  content: string;
  tags: string[];
  relevance: number;
  updatedAt: string;
};

export type ActivityEvent = {
  id: string;
  title: string;
  detail: string;
  agent: string;
  status: "queued" | "running" | "completed" | "blocked";
  createdAt: string;
};

export type WorkspaceSearchResult = {
  id: string;
  title: string;
  type: "project" | "document" | "memory" | "workflow" | "agent";
  snippet: string;
  score: number;
};

"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createId } from "@/lib/id";
import type {
  ActivityEvent,
  WorkspaceDocument,
  WorkspaceMemory,
  WorkspaceProject,
  WorkspaceSearchResult,
  WorkspaceTask,
  WorkspaceWorkflow
} from "@/types/workspace";

type WorkspaceState = {
  workspaceName: string;
  projects: WorkspaceProject[];
  documents: WorkspaceDocument[];
  tasks: WorkspaceTask[];
  workflows: WorkspaceWorkflow[];
  memories: WorkspaceMemory[];
  activity: ActivityEvent[];
};

type WorkspaceActions = {
  createProject: (name?: string) => string;
  addDocument: (doc?: Partial<WorkspaceDocument>) => string;
  createTask: (objective?: string) => string;
  createWorkflow: (goal?: string) => string;
  remember: (memory: Pick<WorkspaceMemory, "title" | "content" | "scope">) => string;
  searchWorkspace: (query: string) => WorkspaceSearchResult[];
  ingestRuntimeEvent: (event: { type: string; title: string; detail?: string }) => void;
  logActivity: (event: Omit<ActivityEvent, "id" | "createdAt">) => void;
  hydrateFromApi: () => Promise<void>;
};

const now = () => new Date().toISOString();

export const useWorkspaceStore = create<WorkspaceState & WorkspaceActions>()(
  persist(
    (set, get) => ({
      workspaceName: "Synzept Workspace",
      projects: [
        {
          id: "proj_1",
          name: "Product Research",
          description: "Market analysis and launch strategy.",
          status: "active",
          tags: ["research"],
          updatedAt: now()
        }
      ],
      documents: [],
      tasks: [],
      workflows: [],
      memories: [],
      activity: [],
      createProject: (name = "Untitled Project") => {
        const id = createId("proj");
        set((s) => ({
          projects: [
            {
              id,
              name,
              description: "New project workspace.",
              status: "active",
              tags: ["new"],
              updatedAt: now()
            },
            ...s.projects
          ]
        }));
        void fetch("/api/workspace/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, description: "New project workspace.", tags: ["new"] }),
          credentials: "include"
        }).catch(() => undefined);
        return id;
      },
      addDocument: (document = {}) => {
        const id = document.id ?? createId("doc");
        set((s) => ({
          documents: [
            {
              id,
              title: document.title ?? "Uploaded document",
              type: document.type ?? "markdown",
              summary: document.summary ?? "Indexed for semantic search.",
              projectId: document.projectId,
              updatedAt: now(),
              chunks: document.chunks ?? 0
            },
            ...s.documents
          ]
        }));
        return id;
      },
      createTask: (objective = "Execute a focused research workflow.") => {
        const id = createId("task");
        set((s) => ({
          tasks: [
            {
              id,
              title: objective.slice(0, 48),
              objective,
              status: "planning",
              progress: 10,
              updatedAt: now()
            },
            ...s.tasks
          ]
        }));
        void fetch("/api/workspace/tasks", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ objective, title: objective.slice(0, 48) }),
          credentials: "include"
        }).catch(() => undefined);
        return id;
      },
      createWorkflow: (goal = "Automate research and synthesis.") => {
        const id = createId("wf");
        set((s) => ({
          workflows: [
            {
              id,
              name: goal.slice(0, 40),
              description: goal,
              category: "research",
              nodes: [
                { id: "n1", type: "trigger", label: "Trigger", x: 20, y: 60 },
                { id: "n2", type: "ai_task", label: "Execute", x: 200, y: 40 },
                { id: "n3", type: "output", label: "Output", x: 400, y: 60 }
              ],
              edges: [
                { id: "e1", from: "n1", to: "n2" },
                { id: "e2", from: "n2", to: "n3" }
              ]
            },
            ...s.workflows
          ]
        }));
        return id;
      },
      remember: (memory) => {
        const id = createId("mem");
        set((s) => ({
          memories: [
            {
              id,
              scope: memory.scope,
              title: memory.title,
              content: memory.content,
              tags: [],
              relevance: 0.8,
              updatedAt: now()
            },
            ...s.memories
          ]
        }));
        return id;
      },
      searchWorkspace: (query) => {
        const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
        const score = (text: string) => terms.reduce((n, t) => n + (text.toLowerCase().includes(t) ? 1 : 0), 0);
        const s = get();
        return [
          ...s.projects.map((p) => ({
            id: p.id,
            title: p.name,
            type: "project" as const,
            snippet: p.description,
            score: score(`${p.name} ${p.description}`)
          })),
          ...s.documents.map((d) => ({
            id: d.id,
            title: d.title,
            type: "document" as const,
            snippet: d.summary,
            score: score(`${d.title} ${d.summary}`)
          })),
          ...s.memories.map((m) => ({
            id: m.id,
            title: m.title,
            type: "memory" as const,
            snippet: m.content,
            score: score(`${m.title} ${m.content}`) + m.relevance
          }))
        ]
          .filter((r) => r.score > 0)
          .sort((a, b) => b.score - a.score)
          .slice(0, 8);
      },
      ingestRuntimeEvent: (event) =>
        set((s) => ({
          activity: [
            {
              id: createId("act"),
              title: event.title,
              detail: event.detail ?? event.type,
              agent: "runtime",
              status: (event.type.includes("completed") ? "completed" : "running") as ActivityEvent["status"],
              createdAt: now()
            },
            ...s.activity
          ].slice(0, 30)
        })),
      logActivity: (event) =>
        set((s) => ({
          activity: [{ ...event, id: createId("act"), createdAt: now() }, ...s.activity].slice(0, 30)
        })),
      hydrateFromApi: async () => {
        try {
          const res = await fetch("/api/workspace/dashboard", { credentials: "include" });
          if (!res.ok) return;
          const payload = (await res.json()) as {
            dashboard?: {
              projects?: WorkspaceProject[];
              tasks?: WorkspaceTask[];
              memories?: Array<{ id: string; content: string; category: string; createdAt: string }>;
            };
          };
          const d = payload.dashboard;
          if (!d) return;
          set((s) => ({
            projects: d.projects?.length ? d.projects : s.projects,
            tasks: d.tasks?.length ? d.tasks : s.tasks,
            memories: d.memories?.length
              ? d.memories.map((m) => ({
                  id: m.id,
                  scope: m.category,
                  title: m.category,
                  content: m.content,
                  tags: [],
                  relevance: 0.85,
                  updatedAt: m.createdAt
                }))
              : s.memories
          }));
        } catch {
          /* offline / backend not running */
        }
      }
    }),
    { name: "synzept-web-workspace" }
  )
);

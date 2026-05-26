import { create } from "zustand";
import type { Dashboard, Note, Project, Task } from "@/lib/api";

type WorkspaceState = {
  dashboard: Dashboard | null;
  projects: Project[];
  notes: Note[];
  tasks: Task[];
  dashboardLoadedAt: string | null;
  isLoading: boolean;
  hasFreshDashboard: (maxAgeMs?: number) => boolean;
  setDashboard: (d: Dashboard) => void;
  setProjects: (p: Project[]) => void;
  setNotes: (n: Note[]) => void;
  setTasks: (t: Task[]) => void;
  setLoading: (v: boolean) => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  dashboard: null,
  projects: [],
  notes: [],
  tasks: [],
  dashboardLoadedAt: null,
  isLoading: false,
  hasFreshDashboard: (maxAgeMs = 60_000) => {
    const loadedAt = get().dashboardLoadedAt;
    return Boolean(loadedAt && Date.now() - new Date(loadedAt).getTime() < maxAgeMs);
  },
  setDashboard: (dashboard) => set({ dashboard, dashboardLoadedAt: new Date().toISOString() }),
  setProjects: (projects) => set({ projects }),
  setNotes: (notes) => set({ notes }),
  setTasks: (tasks) => set({ tasks }),
  setLoading: (isLoading) => set({ isLoading }),
}));

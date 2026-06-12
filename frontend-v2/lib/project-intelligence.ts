import { request } from "@/lib/api";
import type {
  ProjectDecision,
  ProjectIntelligencePage,
  ProjectIntelligenceStatus,
  ProjectOpenLoop,
} from "../types/project-intelligence";

export const projectIntelligenceApi = {
  get: (projectId: string) =>
    request<ProjectIntelligencePage>(`/api/v2/projects/${projectId}/intelligence`),

  update: (
    projectId: string,
    data: Partial<{
      current_focus: string;
      summary: string;
      recommended_next_step: string;
      status: ProjectIntelligenceStatus;
    }>,
  ) =>
    request(`/api/v2/projects/${projectId}/intelligence`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  createDecision: (projectId: string, decision: string) =>
    request<ProjectDecision>(`/api/v2/projects/${projectId}/intelligence/decisions`, {
      method: "POST",
      body: JSON.stringify({ decision }),
    }),

  updateDecision: (projectId: string, decisionId: string, data: Partial<Pick<ProjectDecision, "decision" | "status">>) =>
    request<ProjectDecision>(`/api/v2/projects/${projectId}/intelligence/decisions/${decisionId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  createLoop: (projectId: string, loop: string) =>
    request<ProjectOpenLoop>(`/api/v2/projects/${projectId}/intelligence/open-loops`, {
      method: "POST",
      body: JSON.stringify({ loop }),
    }),

  updateLoop: (projectId: string, loopId: string, data: Partial<Pick<ProjectOpenLoop, "loop" | "status">>) =>
    request<ProjectOpenLoop>(`/api/v2/projects/${projectId}/intelligence/open-loops/${loopId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

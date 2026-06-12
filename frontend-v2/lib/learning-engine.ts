import { request } from "@/lib/api";
import type { LearningEngine, LearningSettings, LearningSuggestion } from "../types/learning-engine";
import type { UserUnderstanding } from "../types/user-understanding";

export const learningEngineApi = {
  get: () => request<LearningEngine>("/api/v2/learning-engine"),
  analyze: () => request<LearningEngine>("/api/v2/learning-engine/analyze", { method: "POST" }),
  updateSettings: (data: Partial<LearningSettings>) =>
    request<LearningSettings>("/api/v2/learning-engine/settings", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  clearHistory: () => request<{ ok: boolean }>("/api/v2/learning-engine/history", { method: "DELETE" }),
  editSuggestion: (id: string, data: Pick<LearningSuggestion, "title" | "description">) =>
    request<LearningSuggestion>(`/api/v2/learning-engine/suggestions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  acceptSuggestion: (id: string) =>
    request<UserUnderstanding>(`/api/v2/learning-engine/suggestions/${id}/accept`, { method: "POST" }),
  ignoreSuggestion: (id: string) =>
    request<LearningSuggestion>(`/api/v2/learning-engine/suggestions/${id}/ignore`, { method: "POST" }),
};

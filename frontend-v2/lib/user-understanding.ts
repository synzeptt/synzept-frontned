import { request } from "@/lib/api";
import type { LearningSuggestion, UserUnderstandingProfile } from "../types/user-understanding";

export const emptyUnderstanding: Omit<UserUnderstandingProfile, "id" | "userId" | "createdAt" | "updatedAt"> = {
  personal: {},
  professional: {},
  goals: {},
  preferences: {},
  learning: {},
  currentFocus: {},
};

export const understandingApi = {
  get: () => request<UserUnderstandingProfile>("/api/user-understanding"),

  create: (data: typeof emptyUnderstanding) =>
    request<UserUnderstandingProfile>("/api/user-understanding", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (data: typeof emptyUnderstanding) =>
    request<UserUnderstandingProfile>("/api/user-understanding", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  remove: (id: string) =>
    request<{ ok: boolean }>(`/api/v2/user-understanding/${id}`, {
      method: "DELETE",
    }),
};

export const learningSuggestionsApi = {
  list: () => request<LearningSuggestion[]>("/api/learning-suggestions"),

  create: (data: Pick<LearningSuggestion, "title" | "description">) =>
    request<LearningSuggestion>("/api/learning-suggestions", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  accept: (id: string) =>
    request<LearningSuggestion>(`/api/learning-suggestions/${id}/accept`, {
      method: "PUT",
    }),

  ignore: (id: string) =>
    request<LearningSuggestion>(`/api/learning-suggestions/${id}/ignore`, {
      method: "PUT",
    }),

  edit: (id: string, data: Partial<Pick<LearningSuggestion, "title" | "description">>) =>
    request<LearningSuggestion>(`/api/learning-suggestions/${id}/edit`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
};

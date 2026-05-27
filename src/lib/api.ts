const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
const TOKEN_KEY = "synzept_access_token";
const REFRESH_KEY = "synzept_refresh_token";
const ACCESS_TOKEN_MAX_AGE_SECONDS = 60 * 30;
const REFRESH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

function backendUrl(path: string): string {
  if (!API_BASE) {
    throw new Error("Synzept is missing its backend URL. Set NEXT_PUBLIC_API_URL and redeploy.");
  }
  return `${API_BASE}${path}`;
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return readStoredValue(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return readStoredValue(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string) {
  writeStoredValue(TOKEN_KEY, access, ACCESS_TOKEN_MAX_AGE_SECONDS);
  writeStoredValue(REFRESH_KEY, refresh, REFRESH_TOKEN_MAX_AGE_SECONDS);
}

export function clearTokens() {
  removeStoredValue(TOKEN_KEY);
  removeStoredValue(REFRESH_KEY);
}

function readStoredValue(key: string): string | null {
  const localValue = readLocalStorage(key);
  if (localValue) return localValue;
  const cookieValue = readCookie(key);
  if (cookieValue) {
    writeLocalStorage(key, cookieValue);
    return cookieValue;
  }
  return null;
}

function writeStoredValue(key: string, value: string, maxAgeSeconds: number) {
  writeLocalStorage(key, value);
  writeCookie(key, value, maxAgeSeconds);
}

function removeStoredValue(key: string) {
  try {
    localStorage.removeItem(key);
  } catch {
    /* ignore unavailable storage */
  }
  document.cookie = `${key}=; Max-Age=0; Path=/; SameSite=Lax; Secure`;
}

function readLocalStorage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeLocalStorage(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* cookie fallback remains available */
  }
}

function readCookie(key: string): string | null {
  const prefix = `${key}=`;
  const cookie = document.cookie
    .split("; ")
    .find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

function writeCookie(key: string, value: string, maxAgeSeconds: number) {
  document.cookie = `${key}=${encodeURIComponent(value)}; Max-Age=${maxAgeSeconds}; Path=/; SameSite=Lax; Secure`;
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function refreshAccessToken(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const response = await fetch(backendUrl("/api/v1/auth/refresh"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!response.ok) return false;
    const data = await response.json();
    setTokens(data.access_token, data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(path: string, options?: RequestInit, retry = true): Promise<T> {
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    throw new Error("You appear to be offline. Your work is still here; reconnect and try again.");
  }
  let response: Response;
  try {
    response = await fetch(backendUrl(path), {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
        ...(options?.headers ?? {}),
      },
    });
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") throw err;
    throw new Error("Synzept could not reach the backend. Your workspace is safe; please try again in a moment.");
  }
  if (response.status === 401 && retry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) return request<T>(path, options, false);
    clearTokens();
    throw new Error("Please sign in again to continue.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const msg = body.message || body.detail;
    throw new Error(typeof msg === "string" ? msg : Array.isArray(msg) ? msg[0]?.msg : "Synzept could not complete that request. Please try again.");
  }
  return response.json();
}

export type ChatMessage = { role: "user" | "assistant" | "system"; content: string; id?: string };

export type Conversation = {
  id: string;
  title: string | null;
  project_id: string | null;
  summary: string | null;
  conversation_type?: string;
  archived_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type Task = {
  id: string;
  title: string;
  description: string | null;
  status: "todo" | "in_progress" | "completed" | "archived" | "pending" | "done";
  priority: string;
  project_id: string | null;
  due_at: string | null;
  created_at: string;
};

export type Note = {
  id: string;
  title: string | null;
  content: string;
  summary?: string | null;
  project_id: string | null;
  created_at: string;
};

export type Project = {
  id: string;
  name: string;
  description: string | null;
  status: string;
  context_summary: string | null;
  created_at: string;
};

export type ProjectContext = {
  project: Project;
  conversations: Conversation[];
  notes: Note[];
  tasks: Task[];
  memories: Memory[];
  continuity_summary: string;
};

export type Memory = {
  id: string;
  content: string;
  category: string;
  memory_type: string;
  importance: number;
  project_id?: string | null;
  created_at: string;
};

export type UsefulnessMetrics = {
  daily_active_days: number;
  conversations_started: number;
  messages_sent: number;
  memory_events: number;
  project_events: number;
  task_events: number;
  onboarding_events: number;
  dashboard_returns: number;
  continuation_cards_opened: number;
  restoration_actions: number;
  feedback_items: number;
  average_response_rating: number | null;
};

export type DailySuggestion = {
  type: string;
  label: string;
  description: string;
};

export type DailyExperience = {
  date: string;
  morning_briefing: string;
  evening_summary: string | null;
  briefing: string;
  workflow_phase?: "morning" | "restore" | "wrap_up" | "closed" | string;
  rhythm_prompt?: string;
  focus_areas: string[];
  suggestions: DailySuggestion[];
  completed_today: string[];
  carry_forward: string[];
  insights: string[];
  tomorrow_priorities?: string[];
  continuation_points?: string[];
  has_evening: boolean;
};

export type RecentActivity = {
  id: string;
  type: "conversation" | "task" | "note" | "project" | string;
  title: string;
  description: string | null;
  project_id: string | null;
  occurred_at: string;
};

export type ContinuityCard = {
  id: string;
  type: "task" | "conversation" | "project" | string;
  title: string;
  description: string;
  action_label: string;
  href: string;
  continuation_prompt?: string;
  reason?: string;
  continuity_score?: number;
  project_id: string | null;
  task_id: string | null;
  conversation_id: string | null;
  priority: string;
  updated_at: string | null;
};

export type ContinuityTheme = {
  label: string;
  summary: string;
  score: number;
  count: number;
  href?: string | null;
};

export type ContinuityTimelineEntry = {
  date: string;
  headline: string;
  summary: string;
  recurring_priorities: string[];
  recurring_themes: string[];
  unresolved_items: string[];
  continuity_score: number;
};

export type DashboardStats = {
  active_projects: number;
  open_tasks: number;
  recent_conversations: number;
  notes_updated: number;
};

export type RetentionSignal = {
  type: string;
  label: string;
  description: string;
  score: number;
  href?: string | null;
};

export type ReturningUser = {
  is_returning: boolean;
  days_since_last_seen: number | null;
  summary: string;
  prompt: string;
  signals: RetentionSignal[];
};

export type Dashboard = {
  projects: Project[];
  recent_conversations?: Conversation[];
  tasks: Task[];
  unfinished_tasks?: Task[];
  notes: Note[];
  memories: Memory[];
  continuity_summary?: string;
  recurring_priorities?: ContinuityTheme[];
  ongoing_themes?: ContinuityTheme[];
  continuity_timeline?: ContinuityTimelineEntry[];
  memory_evolution?: string[];
  priorities: Task[];
  recent_activity?: RecentActivity[];
  continuity_cards?: ContinuityCard[];
  returning_user?: ReturningUser;
  stats?: DashboardStats;
  briefing: string;
  daily?: DailyExperience | null;
  morning_briefing?: string;
  evening_summary?: string | null;
  focus_areas?: string[];
  suggestions?: DailySuggestion[];
};

export type AuthUser = {
  id: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  profile_summary: string | null;
  onboarding_state: string;
  auth_provider: string;
  preferences?: Record<string, unknown>;
};

export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  onboarding_state?: string;
  display_name?: string | null;
};

export type OnboardingStatus = {
  state: string;
  is_complete: boolean;
  display_name: string | null;
  goals: string[];
  has_memories: boolean;
  has_workspace: boolean;
  conversation_id: string | null;
  completed_steps: string[];
  skipped_steps: string[];
  initialized_systems: string[];
  resume_step: string;
  dashboard_preview: OnboardingDashboardPreview;
  analytics: OnboardingAnalyticsSummary;
};

export type OnboardingDashboardPreview = {
  suggested_priorities: string[];
  starter_structure: string[];
  continuity_summary: string;
  next_actions: string[];
};

export type OnboardingAnalyticsSummary = {
  completed: boolean;
  drop_off_step: string | null;
  first_ai_interaction_success: boolean;
  first_project_created: boolean;
  first_memory_initialized: boolean;
  events_tracked: number;
};

export const api = {
  signup: (email: string, password: string) =>
    request<AuthTokens>("/api/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  signupWithInvite: (email: string, password: string, displayName?: string, inviteCode?: string) =>
    request<AuthTokens>("/api/v1/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName, invite_code: inviteCode }),
    }),

  login: (email: string, password: string) =>
    request<AuthTokens>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  forgotPassword: (email: string) =>
    request<{ ok: boolean; message: string }>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resetPassword: (token: string, password: string) =>
    request<{ ok: boolean; message: string }>("/api/v1/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    }),

  googleLogin: (idToken: string) =>
    request<AuthTokens>("/api/v1/auth/google", {
      method: "POST",
      body: JSON.stringify({ id_token: idToken }),
    }),

  logout: () =>
    request<{ ok: boolean }>("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: getRefreshToken() }),
    }).catch(() => ({ ok: true })),

  deleteAccount: (data: { password?: string; confirmation: string }) =>
    request<{ ok: boolean; message: string }>("/api/v1/auth/account", {
      method: "DELETE",
      body: JSON.stringify(data),
    }),

  me: () => request<AuthUser>("/api/v1/auth/me"),

  updatePreferences: (data: {
    memory_enabled?: boolean;
    personalization_enabled?: boolean;
    analytics_enabled?: boolean;
  }) =>
    request<AuthUser>("/api/v1/auth/preferences", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  updateAvatar: (avatarUrl: string | null) =>
    request<AuthUser>("/api/v1/auth/profile/avatar", {
      method: "PATCH",
      body: JSON.stringify({ avatar_url: avatarUrl }),
    }),

  getAccessStatus: () =>
    request<{ early_access_enabled: boolean; invite_required: boolean }>("/api/v1/launch/access"),

  getOnboardingStatus: () => request<OnboardingStatus>("/api/v1/onboarding/status"),

  onboardingWelcome: () =>
    request<OnboardingStatus>("/api/v1/onboarding/welcome", { method: "POST" }),

  onboardingContext: (data: {
    display_name: string;
    primary_role?: string;
    goals: string[];
    current_priorities: string[];
    communication_style: "concise" | "balanced" | "deep";
    work_type?: string;
    productivity_style?: string;
  }) =>
    request<OnboardingStatus>("/api/v1/onboarding/context", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  onboardingWorkspace: (data: {
    create_project?: boolean;
    project_name?: string;
    project_description?: string;
    first_goal?: string;
    first_task?: string;
    first_note?: string;
    skipped?: boolean;
  }) =>
    request<OnboardingStatus>("/api/v1/onboarding/workspace", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  onboardingInitializeMemories: () =>
    request<OnboardingStatus>("/api/v1/onboarding/initialize-memories", { method: "POST" }),

  onboardingFirstChat: (data?: { message?: string; use_suggested_prompt?: boolean }) =>
    request<{ conversation_id: string; reply: string; suggestions: Array<{ label: string; description: string }> }>(
      "/api/v1/onboarding/first-chat",
      { method: "POST", body: JSON.stringify(data ?? { use_suggested_prompt: true }) },
    ),

  onboardingComplete: () =>
    request<{
      welcome_message: string;
      tasks_created: number;
      memories_created: number;
      dashboard_preview: OnboardingDashboardPreview;
      analytics: OnboardingAnalyticsSummary;
    }>(
      "/api/v1/onboarding/complete",
      { method: "POST" },
    ),

  onboardingSkip: () =>
    request<{ welcome_message: string }>("/api/v1/onboarding/skip", { method: "POST" }),

  getDashboard: () => request<Dashboard>("/api/v1/dashboard"),

  joinWaitlist: (data: { email: string; name?: string; role?: string; intended_use?: string }) =>
    request<{ id: string; email: string; status: string; created_at: string }>("/api/v1/launch/waitlist", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  createInvite: (data: { email?: string; max_uses?: number; notes?: string }) =>
    request<{ code: string; email: string | null; max_uses: number; use_count: number }>("/api/v1/launch/invites", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  sendFeedback: (data: {
    feedback_type: "issue" | "suggestion" | "response_rating" | "memory_issue" | "bug" | "support";
    message?: string;
    rating?: number;
    conversation_id?: string;
    message_id?: string;
    memory_id?: string;
    metadata?: Record<string, unknown>;
  }) =>
    request<{ id: string; feedback_type: string; status: string }>("/api/v1/feedback", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  sendMemoryFeedback: (data: {
    memory_id?: string;
    signal: "relevant" | "not_relevant" | "incorrect" | "missing_context" | "useful" | "not_useful" | "edited" | "removed";
    rating?: number;
    corrected_context?: string;
    metadata?: Record<string, unknown>;
  }) =>
    request<{ ok: boolean; id: string }>("/api/v1/feedback/memory", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  trackEvent: (event_type: string, surface?: string, metadata?: Record<string, unknown>, value?: number) => {
    if (!getAccessToken()) return Promise.resolve({ ok: false });
    return request<{ ok: boolean }>("/api/v1/analytics/event", {
      method: "POST",
      body: JSON.stringify({ event_type, surface, metadata: metadata ?? {}, value }),
    }).catch(() => ({ ok: false }));
  },

  getUsefulnessMetrics: () => request<UsefulnessMetrics>("/api/v1/analytics/usefulness"),

  listConversations: () => request<Conversation[]>("/api/v1/conversations"),

  getMessages: (conversationId: string) =>
    request<Array<{ id: string; role: string; content: string; conversation_id: string }>>(
      `/api/v1/conversations/${conversationId}/messages`,
    ),

  sendMessage: (message: string, conversationId?: string, projectId?: string) =>
    request<{ conversation_id: string; message_id: string; reply: string }>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId, project_id: projectId }),
    }),

  streamMessage: async function* (
    message: string,
    conversationId?: string,
    projectId?: string,
    signal?: AbortSignal,
  ): AsyncGenerator<{ type: string; content?: string; conversation_id?: string }> {
    if (typeof navigator !== "undefined" && !navigator.onLine) {
      throw new Error("You appear to be offline. Your message is still here; reconnect and try again.");
    }
    let response: Response;
    try {
      response = await fetch(backendUrl("/api/v1/chat/stream"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ message, conversation_id: conversationId, project_id: projectId }),
        signal,
      });
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") throw err;
      throw new Error("Synzept could not reach the backend to start streaming. Your message is still here; retry when the server is ready.");
    }
    if (response.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        response = await fetch(backendUrl("/api/v1/chat/stream"), {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({ message, conversation_id: conversationId, project_id: projectId }),
          signal,
        });
      } else {
        clearTokens();
      }
    }
    if (!response.ok || !response.body) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.message || "Synzept could not start the response. Please retry.");
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let eventType = "message";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";
      for (const event of events) {
        const lines = event.split("\n");
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
          try {
            const data = JSON.parse(line.slice(6));
            if (eventType === "token") yield { type: "token", content: data.content };
            else if (eventType === "meta") yield { type: "meta", conversation_id: data.conversation_id };
            else if (eventType === "done") yield { type: "done", conversation_id: data.conversation_id };
            else if (eventType === "error") throw new Error(data.message || "Stream error");
          } catch (e) {
            if (e instanceof Error && e.message !== "Stream error") throw e;
          }
          }
        }
        eventType = "message";
      }
    }
  },

  listTasks: (status?: string, projectId?: string) => {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (projectId) params.set("project_id", projectId);
    const query = params.toString();
    return request<Task[]>(`/api/v1/tasks${query ? `?${query}` : ""}`);
  },

  createTask: (data: { title: string; description?: string; priority?: string; project_id?: string }) =>
    request<Task>("/api/v1/tasks", { method: "POST", body: JSON.stringify(data) }),

  updateTask: (id: string, data: Partial<Task>) =>
    request<Task>(`/api/v1/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  listNotes: (projectId?: string, q?: string) => {
    const params = new URLSearchParams();
    if (projectId) params.set("project_id", projectId);
    if (q) params.set("q", q);
    const query = params.toString();
    return request<Note[]>(`/api/v1/notes${query ? `?${query}` : ""}`);
  },

  createNote: (data: { title?: string; content: string; project_id?: string }) =>
    request<Note>("/api/v1/notes", { method: "POST", body: JSON.stringify(data) }),

  updateNote: (id: string, data: Partial<Pick<Note, "title" | "content" | "project_id" | "summary">>) =>
    request<Note>(`/api/v1/notes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  deleteNote: (id: string) =>
    request<{ ok: boolean }>(`/api/v1/notes/${id}`, { method: "DELETE" }),

  listProjects: () => request<Project[]>("/api/v1/projects"),

  createProject: (data: { name: string; description?: string }) =>
    request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),

  getProject: (id: string) => request<Project>(`/api/v1/projects/${id}`),

  updateProject: (id: string, data: Partial<Pick<Project, "name" | "description" | "status" | "context_summary">>) =>
    request<Project>(`/api/v1/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  archiveProject: (id: string) =>
    request<Project>(`/api/v1/projects/${id}/archive`, { method: "PATCH" }),

  getProjectContext: (id: string) => request<ProjectContext>(`/api/v1/projects/${id}/context`),

  createConversation: (data: { title?: string; project_id?: string }) =>
    request<Conversation>("/api/v1/conversations", { method: "POST", body: JSON.stringify(data) }),

  listMemories: () => request<Memory[]>("/api/v1/memories"),

  updateMemory: (id: string, data: Partial<Pick<Memory, "content" | "category" | "importance">>) =>
    request<Memory>(`/api/v1/memories/${id}`, { method: "PATCH", body: JSON.stringify(data) }),

  deleteMemory: (id: string) =>
    request<{ ok: boolean }>(`/api/v1/memories/${id}`, { method: "DELETE" }),

  getBriefing: () => request<{ briefing: string }>("/api/v1/briefing"),

  getDailyToday: () => request<DailyExperience>("/api/v1/daily/today"),

  regenerateDaily: (kind: "morning" | "evening" = "morning") =>
    request<DailyExperience>(`/api/v1/daily/regenerate?kind=${kind}`, { method: "POST" }),

  closeDay: () => request<DailyExperience>("/api/v1/daily/evening/close", { method: "POST" }),

  saveDailyWrapUp: (data: {
    progress_summary?: string;
    completed?: string[];
    unfinished?: string[];
    insights?: string[];
    tomorrow_priorities?: string[];
    continuation_points?: string[];
  }) =>
    request<DailyExperience>("/api/v1/daily/wrap-up", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  clearTokens,
};

export function routeAfterAuth(onboardingState: string): string {
  return onboardingState === "complete" ? "/dashboard" : "/onboarding";
}

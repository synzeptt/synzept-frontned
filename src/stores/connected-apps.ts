import { create } from "zustand";
import { api, clearSynzeptContextCache, type ConnectedApp } from "@/lib/api";

type ConnectedAppsState = {
  apps: Record<string, ConnectedApp | null>;
  loadedAt: number | null;
  isLoading: boolean;
  error: string | null;
  refresh: (force?: boolean) => Promise<Record<string, ConnectedApp | null>>;
  setApp: (provider: string, app: ConnectedApp | null) => void;
  invalidateContext: () => void;
  isConnected: (provider: string) => boolean;
};

let refreshPromise: Promise<Record<string, ConnectedApp | null>> | null = null;
const FRESH_MS = 20_000;

export const useConnectedAppsStore = create<ConnectedAppsState>((set, get) => ({
  apps: {},
  loadedAt: null,
  isLoading: false,
  error: null,
  refresh: async (force = false) => {
    const { apps, loadedAt } = get();
    if (!force && loadedAt && Date.now() - loadedAt < FRESH_MS) return apps;
    if (refreshPromise) return refreshPromise;

    set({ isLoading: true, error: null });
    refreshPromise = Promise.all([api.getGoogleCalendarStatus(), api.getGoogleWorkspaceStatuses(), api.getMicrosoft365Statuses(), api.getGitHubStatus(), api.getSlackStatus(), api.getNotionStatus()])
      .then(([calendarStatus, workspaceStatuses, microsoftStatuses, githubStatus, slackStatus, notionStatus]) => {
        const next: Record<string, ConnectedApp | null> = { google_calendar: calendarStatus, github: githubStatus, slack: slackStatus, notion: notionStatus };
        for (const app of workspaceStatuses) next[app.provider] = app;
        for (const app of microsoftStatuses) next[app.provider] = app;
        set({ apps: next, loadedAt: Date.now(), isLoading: false, error: null });
        return next;
      })
      .catch((error) => {
        set({ isLoading: false, error: error instanceof Error ? error.message : "Connected app status could not load." });
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
    return refreshPromise;
  },
  setApp: (provider, app) => set((state) => ({ apps: { ...state.apps, [provider]: app }, loadedAt: Date.now() })),
  invalidateContext: () => {
    clearSynzeptContextCache("google-calendar");
    clearSynzeptContextCache("google-calendar-weekly");
    clearSynzeptContextCache("dashboard");
    clearSynzeptContextCache("s1-home");
    clearSynzeptContextCache("daily");
    clearSynzeptContextCache("continuity-mode");
    clearSynzeptContextCache("open-loops-engine");
    clearSynzeptContextCache("understanding");
    clearSynzeptContextCache("microsoft-calendar");
    clearSynzeptContextCache("microsoft-calendar-weekly");
  },
  isConnected: (provider) => Boolean(get().apps[provider]?.connected),
}));

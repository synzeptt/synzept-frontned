import { create } from "zustand";
import { api, getAccessToken, getRefreshToken, refreshAccessToken, routeAfterAuth, setTokens, type AuthUser } from "@/lib/api";

type AuthState = {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<string>;
  signup: (email: string, password: string) => Promise<string>;
  googleLogin: (idToken: string) => Promise<string>;
  logout: () => Promise<void>;
  deleteAccount: (password: string | undefined, confirmation: string) => Promise<void>;
  hydrate: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateAvatar: (avatarUrl: string | null) => Promise<void>;
};

let hydratePromise: Promise<void> | null = null;

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email, password) => {
    const tokens = await api.login(email, password);
    setTokens(tokens.access_token, tokens.refresh_token);
    const user = await api.me();
    set({ user, isAuthenticated: true, isLoading: false });
    return routeAfterAuth(user.onboarding_state);
  },

  signup: async (email, password) => {
    const tokens = await api.signup(email, password);
    setTokens(tokens.access_token, tokens.refresh_token);
    const user = await api.me();
    set({ user, isAuthenticated: true, isLoading: false });
    return routeAfterAuth(user.onboarding_state);
  },

  googleLogin: async (idToken) => {
    const tokens = await api.googleLogin(idToken);
    setTokens(tokens.access_token, tokens.refresh_token);
    const user = await api.me();
    set({ user, isAuthenticated: true, isLoading: false });
    return routeAfterAuth(user.onboarding_state);
  },

  logout: async () => {
    await api.logout();
    api.clearTokens();
    set({ user: null, isAuthenticated: false });
  },

  deleteAccount: async (password, confirmation) => {
    await api.deleteAccount({ password, confirmation });
    api.clearTokens();
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  hydrate: async () => {
    if (hydratePromise) return hydratePromise;

    hydratePromise = (async () => {
      set({ isLoading: true });

      const hasAccessToken = Boolean(getAccessToken());
      const hasRefreshToken = Boolean(getRefreshToken());

      if (!hasAccessToken && !hasRefreshToken) {
        set({ isLoading: false, isAuthenticated: false });
        return;
      }

      try {
        if (!hasAccessToken) {
          const refreshed = await refreshAccessToken();
          if (!refreshed) {
            set({ user: null, isAuthenticated: false, isLoading: false });
            return;
          }
        }
        const user = await api.me();
        set({ user, isAuthenticated: true, isLoading: false });
      } catch {
        set({ user: null, isAuthenticated: false, isLoading: false });
      }
    })().finally(() => {
      hydratePromise = null;
    });

    return hydratePromise;
  },

  refreshUser: async () => {
    try {
      const user = await api.me();
      set({ user });
    } catch {
      /* ignore */
    }
  },

  updateAvatar: async (avatarUrl) => {
    const user = await api.updateAvatar(avatarUrl);
    set({ user });
  },
}));

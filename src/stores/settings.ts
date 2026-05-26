import { create } from "zustand";
import { persist } from "zustand/middleware";

export type Appearance = "dark" | "light";

const THEME_KEY = "synzept-theme";

function persistAppearance(appearance: Appearance) {
  if (typeof window !== "undefined") {
    localStorage.setItem(THEME_KEY, appearance);
  }
}

type SettingsState = {
  appearance: Appearance;
  memoryEnabled: boolean;
  personalizationEnabled: boolean;
  analyticsEnabled: boolean;
  setAppearance: (a: Appearance) => void;
  setMemoryEnabled: (v: boolean) => void;
  setPersonalizationEnabled: (v: boolean) => void;
  setAnalyticsEnabled: (v: boolean) => void;
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      appearance: "light",
      memoryEnabled: true,
      personalizationEnabled: true,
      analyticsEnabled: true,
      setAppearance: (appearance) => {
        persistAppearance(appearance);
        set({ appearance });
      },
      setMemoryEnabled: (memoryEnabled) => set({ memoryEnabled }),
      setPersonalizationEnabled: (personalizationEnabled) => set({ personalizationEnabled }),
      setAnalyticsEnabled: (analyticsEnabled) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("synzept-analytics-enabled", String(analyticsEnabled));
        }
        set({ analyticsEnabled });
      },
    }),
    {
      name: "synzept-settings",
      version: 2,
      partialize: (state) => ({
        memoryEnabled: state.memoryEnabled,
        personalizationEnabled: state.personalizationEnabled,
        analyticsEnabled: state.analyticsEnabled,
      }),
      migrate: (persistedState) => {
        const state = persistedState as Partial<SettingsState>;
        return {
          memoryEnabled: state.memoryEnabled ?? true,
          personalizationEnabled: state.personalizationEnabled ?? true,
          analyticsEnabled: state.analyticsEnabled ?? true,
        };
      },
    },
  ),
);

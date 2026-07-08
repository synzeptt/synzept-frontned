"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { SettingsState } from "@/types/settings";

type SettingsActions = {
  setTone: (tone: SettingsState["tone"]) => void;
  toggleTool: (tool: SettingsState["enabledTools"][number]) => void;
  setMemoryEnabled: (enabled: boolean) => void;
};

export const useSettingsStore = create<SettingsState & SettingsActions>()(
  persist(
    (set) => ({
      model: "gpt-4o-mini",
      temperature: 0.7,
      tone: "balanced",
      enabledTools: ["calculator", "web_search"],
      memoryEnabled: true,
      setTone: (tone) => set({ tone }),
      toggleTool: (tool) =>
        set((s) => ({
          enabledTools: s.enabledTools.includes(tool)
            ? s.enabledTools.filter((t) => t !== tool)
            : [...s.enabledTools, tool]
        })),
      setMemoryEnabled: (enabled) => set({ memoryEnabled: enabled })
    }),
    { name: "synzept-web-settings" }
  )
);

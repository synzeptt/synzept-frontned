"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

type UiState = {
  sidebarCollapsed: boolean;
  mobileNavOpen: boolean;
};

type UiActions = {
  toggleSidebar: () => void;
  setMobileNavOpen: (open: boolean) => void;
};

export const useUiStore = create<UiState & UiActions>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      mobileNavOpen: false,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setMobileNavOpen: (mobileNavOpen) => set({ mobileNavOpen })
    }),
    { name: "synzept-web-ui" }
  )
);

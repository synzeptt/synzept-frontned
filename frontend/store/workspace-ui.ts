"use client";

import { create } from "zustand";

type WorkspaceUIState = {
  sidebarOpen: boolean;
  conversationPanelOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  setConversationPanelOpen: (open: boolean) => void;
};

export const useWorkspaceUIStore = create<WorkspaceUIState>((set) => ({
  sidebarOpen: false,
  conversationPanelOpen: true,
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setConversationPanelOpen: (conversationPanelOpen) => set({ conversationPanelOpen }),
}));

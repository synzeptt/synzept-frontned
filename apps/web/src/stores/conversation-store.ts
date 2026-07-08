"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createId } from "@/lib/id";
import type { Conversation } from "@/types/chat";

type ConversationState = {
  conversations: Conversation[];
  activeConversationId: string | null;
  searchQuery: string;
};

type ConversationActions = {
  createConversation: () => string;
  renameConversation: (id: string, title: string) => void;
  deleteConversation: (id: string) => void;
  setActiveConversation: (id: string) => void;
  setSearchQuery: (query: string) => void;
  attachMessage: (conversationId: string, messageId: string) => void;
  touchConversation: (id: string) => void;
};

function createConversationRecord(): Conversation {
  const now = new Date().toISOString();
  return { id: createId("conv"), title: "New conversation", createdAt: now, updatedAt: now, messageIds: [] };
}

export const useConversationStore = create<ConversationState & ConversationActions>()(
  persist(
    (set) => ({
      conversations: [],
      activeConversationId: null,
      searchQuery: "",
      createConversation: () => {
        const conversation = createConversationRecord();
        set((s) => ({ conversations: [conversation, ...s.conversations], activeConversationId: conversation.id }));
        return conversation.id;
      },
      renameConversation: (id, title) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === id ? { ...c, title: title.trim() || "Untitled" } : c
          )
        })),
      deleteConversation: (id) =>
        set((s) => {
          const conversations = s.conversations.filter((c) => c.id !== id);
          return {
            conversations,
            activeConversationId: s.activeConversationId === id ? conversations[0]?.id ?? null : s.activeConversationId
          };
        }),
      setActiveConversation: (id) => set({ activeConversationId: id }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      attachMessage: (conversationId, messageId) =>
        set((s) => ({
          conversations: s.conversations.map((c) =>
            c.id === conversationId && !c.messageIds.includes(messageId)
              ? { ...c, messageIds: [...c.messageIds, messageId], updatedAt: new Date().toISOString() }
              : c
          )
        })),
      touchConversation: (id) =>
        set((s) => ({
          conversations: s.conversations
            .map((c) => (c.id === id ? { ...c, updatedAt: new Date().toISOString() } : c))
            .sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
        }))
    }),
    {
      name: "synzept-web-conversations",
      onRehydrateStorage: () => (state) => {
        if (state && state.conversations.length === 0) {
          const id = state.createConversation();
          state.setActiveConversation(id);
        }
      }
    }
  )
);

import { create } from "zustand";
import type { ChatMessage, Conversation } from "@/lib/api";

type ChatState = {
  conversations: Conversation[];
  activeConversationId: string | null;
  activeProjectId: string | null;
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  conversationsLoadedAt: string | null;
  messagesByConversation: Record<string, ChatMessage[]>;
  hasFreshConversations: (maxAgeMs?: number) => boolean;
  setConversations: (c: Conversation[]) => void;
  setActiveConversation: (id: string | null) => void;
  setActiveProject: (id: string | null) => void;
  setMessages: (m: ChatMessage[]) => void;
  appendMessage: (m: ChatMessage) => void;
  updateLastAssistant: (content: string) => void;
  removeLastMessage: () => void;
  setStreaming: (v: boolean) => void;
  setError: (e: string | null) => void;
  reset: () => void;
};

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  activeProjectId: null,
  messages: [],
  isStreaming: false,
  error: null,
  conversationsLoadedAt: null,
  messagesByConversation: {},

  hasFreshConversations: (maxAgeMs = 60_000) => {
    const loadedAt = get().conversationsLoadedAt;
    return Boolean(loadedAt && Date.now() - new Date(loadedAt).getTime() < maxAgeMs);
  },
  setConversations: (conversations) => set({ conversations, conversationsLoadedAt: new Date().toISOString() }),
  setActiveConversation: (activeConversationId) => set({ activeConversationId }),
  setActiveProject: (activeProjectId) => set({ activeProjectId }),
  setMessages: (messages) =>
    set((state) => ({
      messages,
      messagesByConversation: state.activeConversationId
        ? { ...state.messagesByConversation, [state.activeConversationId]: messages }
        : state.messagesByConversation,
    })),
  appendMessage: (m) =>
    set((s) => {
      const messages = [...s.messages, m];
      return {
        messages,
        messagesByConversation: s.activeConversationId
          ? { ...s.messagesByConversation, [s.activeConversationId]: messages }
          : s.messagesByConversation,
      };
    }),
  updateLastAssistant: (content) =>
    set((s) => {
      const copy = [...s.messages];
      const last = copy.length - 1;
      if (last >= 0 && copy[last].role === "assistant") {
        copy[last] = { ...copy[last], content };
      }
      return {
        messages: copy,
        messagesByConversation: s.activeConversationId
          ? { ...s.messagesByConversation, [s.activeConversationId]: copy }
          : s.messagesByConversation,
      };
    }),
  removeLastMessage: () =>
    set((s) => {
      const messages = s.messages.slice(0, -1);
      return {
        messages,
        messagesByConversation: s.activeConversationId
          ? { ...s.messagesByConversation, [s.activeConversationId]: messages }
          : s.messagesByConversation,
      };
    }),
  setStreaming: (isStreaming) => set({ isStreaming }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      activeConversationId: null,
      messages: [],
      error: null,
      isStreaming: false,
    }),
}));

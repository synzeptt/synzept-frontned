"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatMessage } from "@/types/chat";

type ChatState = {
  messages: Record<string, ChatMessage>;
  isStreaming: boolean;
  error: string | null;
};

type ChatActions = {
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  appendToMessage: (id: string, chunk: string) => void;
  setStreaming: (streaming: boolean) => void;
  setError: (error: string | null) => void;
};

export const useChatStore = create<ChatState & ChatActions>()(
  persist(
    (set) => ({
      messages: {},
      isStreaming: false,
      error: null,
      addMessage: (message) => set((s) => ({ messages: { ...s.messages, [message.id]: message } })),
      updateMessage: (id, patch) =>
        set((s) => ({ messages: { ...s.messages, [id]: { ...s.messages[id], ...patch } } })),
      appendToMessage: (id, chunk) =>
        set((s) => ({
          messages: {
            ...s.messages,
            [id]: { ...s.messages[id], content: `${s.messages[id]?.content ?? ""}${chunk}` }
          }
        })),
      setStreaming: (isStreaming) => set({ isStreaming }),
      setError: (error) => set({ error })
    }),
    { name: "synzept-web-chat" }
  )
);

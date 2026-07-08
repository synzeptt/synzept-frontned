"use client";

import { useRef, useMemo } from "react";
import { createId } from "@/lib/id";
import { streamAssistantResponse } from "@/services/chat-client";
import { useChatStore } from "@/stores/chat-store";
import { useConversationStore } from "@/stores/conversation-store";
import { useMemoryStore } from "@/stores/memory-store";
import { useSettingsStore } from "@/stores/settings-store";
import type { ChatMessage } from "@/types/chat";

function titleFromPrompt(prompt: string): string {
  const clean = prompt.replace(/\s+/g, " ").trim();
  return clean.length > 44 ? `${clean.slice(0, 44)}...` : clean || "New conversation";
}

export function useChatActions() {
  const abortRef = useRef<AbortController | null>(null);
  const settings = useSettingsStore();
  const memory = useMemoryStore();
  const conversations = useConversationStore();
  const chat = useChatStore();

  return useMemo(
    () => ({
      async sendMessage(content: string) {
        const trimmed = content.trim();
        if (!trimmed || chat.isStreaming) return;

        const conversationId = conversations.activeConversationId ?? conversations.createConversation();
        const userMessage: ChatMessage = {
          id: createId("msg"),
          conversationId,
          role: "user",
          content: trimmed,
          createdAt: new Date().toISOString(),
          status: "complete"
        };
        const assistantMessage: ChatMessage = {
          id: createId("msg"),
          conversationId,
          role: "assistant",
          content: "",
          createdAt: new Date().toISOString(),
          status: "streaming"
        };

        const active = conversations.conversations.find((c) => c.id === conversationId);
        if (active?.messageIds.length === 0) {
          conversations.renameConversation(conversationId, titleFromPrompt(trimmed));
        }

        chat.addMessage(userMessage);
        chat.addMessage(assistantMessage);
        conversations.attachMessage(conversationId, userMessage.id);
        conversations.attachMessage(conversationId, assistantMessage.id);
        conversations.touchConversation(conversationId);
        memory.rememberShortTerm(`User: ${trimmed}`);
        chat.setStreaming(true);
        chat.setError(null);

        const history =
          active?.messageIds
            .map((id) => chat.messages[id])
            .filter(Boolean)
            .slice(-14)
            .map(({ role, content: c }) => ({ role, content: c })) ?? [];

        abortRef.current = new AbortController();

        try {
          await streamAssistantResponse(
            {
              conversationId,
              messages: [...history, { role: "user", content: trimmed }],
              memory: settings.memoryEnabled ? memory.snapshot() : undefined,
              tools: settings.enabledTools
            },
            {
              signal: abortRef.current.signal,
              onChunk: (chunk) => chat.appendToMessage(assistantMessage.id, chunk),
              onComplete: () => {
                chat.updateMessage(assistantMessage.id, { status: "complete" });
                chat.setStreaming(false);
              },
              onError: (error) => {
                chat.updateMessage(assistantMessage.id, {
                  status: "error",
                  content: error.message
                });
                chat.setStreaming(false);
                chat.setError(error.message);
              }
            }
          );
        } catch {
          chat.setStreaming(false);
        }
      },
      cancelGeneration() {
        abortRef.current?.abort();
        chat.setStreaming(false);
      }
    }),
    [chat, conversations, memory, settings]
  );
}

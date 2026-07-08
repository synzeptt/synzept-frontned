"use client";

import { AnimatePresence } from "framer-motion";
import { Sparkles } from "lucide-react";
import { useMemo } from "react";
import { ChatComposer } from "@/components/chat/chat-composer";
import { MessageBubble } from "@/components/chat/message-bubble";
import { useAutoScroll } from "@/hooks/use-auto-scroll";
import { useChatStore } from "@/stores/chat-store";
import { useConversationStore } from "@/stores/conversation-store";

export function ChatPanel() {
  const activeId = useConversationStore((s) => s.activeConversationId);
  const conversation = useConversationStore((s) => s.conversations.find((c) => c.id === s.activeConversationId));
  const messages = useChatStore((s) => s.messages);

  const visible = useMemo(
    () => conversation?.messageIds.map((id) => messages[id]).filter(Boolean) ?? [],
    [conversation?.messageIds, messages]
  );

  const scrollRef = useAutoScroll(visible.map((m) => m.content).join(""));

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        {!activeId || visible.length === 0 ? (
          <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center text-center">
            <div className="mb-4 grid size-14 place-items-center rounded-2xl bg-primary/15 text-primary shadow-glow">
              <Sparkles size={24} />
            </div>
            <h2 className="text-2xl font-semibold tracking-tight">How can Synzept help?</h2>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              Ask questions, run research, draft documents, or explore your workspace with streaming AI responses.
            </p>
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-6">
            <AnimatePresence initial={false}>
              {visible.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
            </AnimatePresence>
            <div ref={scrollRef} />
          </div>
        )}
      </div>
      <ChatComposer />
    </div>
  );
}

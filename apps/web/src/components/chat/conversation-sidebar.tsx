"use client";

import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatConversationDate } from "@/lib/date";
import { cn } from "@/lib/utils";
import { useConversationStore } from "@/stores/conversation-store";

export function ConversationSidebar() {
  const {
    conversations,
    activeConversationId,
    createConversation,
    setActiveConversation,
    deleteConversation
  } = useConversationStore();

  return (
    <aside className="hidden w-64 shrink-0 border-r border-border/60 bg-card/30 md:flex md:flex-col">
      <div className="border-b border-border/60 p-3">
        <Button variant="primary" className="w-full" onClick={createConversation}>
          <Plus size={16} />
          New chat
        </Button>
      </div>
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={cn(
              "group flex w-full items-start gap-2 rounded-lg px-2 py-2 text-sm transition",
              activeConversationId === c.id ? "bg-primary/12 text-primary" : "hover:bg-secondary"
            )}
          >
            <button type="button" onClick={() => setActiveConversation(c.id)} className="flex min-w-0 flex-1 items-start gap-2 text-left">
              <MessageSquare size={14} className="mt-0.5 shrink-0" />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{c.title}</span>
                <span className="text-xs text-muted-foreground">{formatConversationDate(c.updatedAt)}</span>
              </span>
            </button>
            <button
              type="button"
              onClick={() => deleteConversation(c.id)}
              className="shrink-0 opacity-0 transition group-hover:opacity-100"
              aria-label="Delete conversation"
            >
              <Trash2 size={14} className="text-muted-foreground hover:text-red-400" />
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}

"use client";

import { motion } from "framer-motion";
import { AlertCircle, Bot, User } from "lucide-react";
import { MarkdownRenderer } from "@/components/markdown/markdown-renderer";
import { formatMessageTime } from "@/lib/date";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types/chat";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const isError = message.status === "error";

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-3", isUser && "flex-row-reverse")}
    >
      <div
        className={cn(
          "grid size-8 shrink-0 place-items-center rounded-lg",
          isUser ? "bg-accent/20 text-accent" : "bg-primary/15 text-primary"
        )}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className={cn("min-w-0 max-w-[85%]", isUser && "text-right")}>
        <div
          className={cn(
            "rounded-2xl border px-4 py-3 text-left",
            isError && "border-red-500/30 bg-red-500/10 text-red-100",
            isUser && !isError && "border-accent/20 bg-accent/10",
            !isUser && !isError && "border-border bg-card/80"
          )}
        >
          {isError ? (
            <div className="flex gap-2 text-sm">
              <AlertCircle size={16} className="shrink-0" />
              {message.content}
            </div>
          ) : message.content ? (
            <div className="prose prose-invert prose-sm max-w-none prose-p:my-2 prose-pre:m-0">
              <MarkdownRenderer content={message.content} />
            </div>
          ) : (
            <div className="flex gap-1 py-1">
              <span className="typing-dot size-2 rounded-full bg-primary" />
              <span className="typing-dot size-2 rounded-full bg-primary" />
              <span className="typing-dot size-2 rounded-full bg-primary" />
            </div>
          )}
        </div>
        <p className="mt-1 text-[11px] text-muted-foreground">{formatMessageTime(message.createdAt)}</p>
      </div>
    </motion.article>
  );
}

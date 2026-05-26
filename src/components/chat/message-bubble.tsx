"use client";

import { memo, useState } from "react";
import { motion } from "framer-motion";
import { Check, Copy, ThumbsDown, ThumbsUp } from "lucide-react";
import { Markdown } from "./markdown";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";

type Props = {
  role: "user" | "assistant" | "system";
  content: string;
  isStreaming?: boolean;
};

function MessageBubbleComponent({ role, content, isStreaming }: Props) {
  const [copied, setCopied] = useState(false);
  const [rated, setRated] = useState<"up" | "down" | null>(null);
  const isUser = role === "user";

  const copy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const rate = async (rating: 1 | 5) => {
    setRated(rating === 5 ? "up" : "down");
    await api.sendFeedback({
      feedback_type: "response_rating",
      rating,
      message: rating === 5 ? "Useful response" : "Response needs improvement",
      metadata: { surface: "chat" },
    }).catch(() => undefined);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("group flex w-full", isUser ? "justify-end" : "justify-start")}
    >
      <div
        className={cn(
          "relative max-w-[min(100%,42rem)] rounded-xl px-4 py-3.5",
          isUser
            ? "bg-stone-900 text-white"
            : "border border-border bg-white text-stone-700 shadow-soft",
        )}
      >
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-widest text-muted">
          {isUser ? "You" : "Synzept"}
        </p>
        {isUser ? (
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{content}</p>
        ) : (
          <Markdown content={content || (isStreaming ? " " : "")} />
        )}
        {isStreaming && !content && (
          <span className="inline-flex gap-1 py-1">
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-accent" />
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-accent [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-accent [animation-delay:300ms]" />
          </span>
        )}
        {!isUser && content && !isStreaming && (
          <div className="absolute right-2 top-2 flex gap-1 opacity-0 transition group-hover:opacity-100">
            <button
              type="button"
              onClick={() => rate(5)}
              className={cn("rounded-lg p-1.5 text-muted hover:bg-stone-100 hover:text-stone-900", rated === "up" && "text-accent")}
              aria-label="Mark response useful"
              title="Useful"
            >
              <ThumbsUp className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => rate(1)}
              className={cn("rounded-lg p-1.5 text-muted hover:bg-stone-100 hover:text-stone-900", rated === "down" && "text-red-600")}
              aria-label="Mark response not useful"
              title="Not useful"
            >
              <ThumbsDown className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={copy}
              className="rounded-lg p-1.5 text-muted hover:bg-stone-100 hover:text-stone-900"
              aria-label="Copy"
              title="Copy"
            >
              {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export const MessageBubble = memo(MessageBubbleComponent);

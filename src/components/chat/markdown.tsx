"use client";

import { memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/cn";

function MarkdownComponent({ content, className }: { content: string; className?: string }) {
  return (
    <div className={cn("prose-synzept max-w-none", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}

export const Markdown = memo(MarkdownComponent);

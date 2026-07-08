"use client";

import { ArrowUp, Loader2, Square } from "lucide-react";
import { FormEvent, KeyboardEvent, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { useChatActions } from "@/hooks/use-chat-actions";
import { useChatStore } from "@/stores/chat-store";

export function ChatComposer() {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const { sendMessage, cancelGeneration } = useChatActions();

  async function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!value.trim() || isStreaming) return;
    const msg = value;
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    await sendMessage(msg);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void submit();
    }
    if (e.key === "Escape" && isStreaming) cancelGeneration();
  }

  return (
    <form onSubmit={submit} className="border-t border-border/60 bg-background/80 p-4 backdrop-blur-xl">
      <div className="mx-auto max-w-3xl">
        <div className="surface flex items-end gap-2 p-2">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
            }}
            onKeyDown={onKeyDown}
            rows={1}
            disabled={isStreaming}
            placeholder="Message Synzept..."
            className="max-h-40 min-h-10 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none placeholder:text-muted-foreground"
          />
          {isStreaming ? (
            <Button type="button" variant="outline" size="icon" onClick={cancelGeneration}>
              <Square size={16} />
            </Button>
          ) : (
            <Button type="submit" variant="primary" size="icon" disabled={!value.trim()}>
              <ArrowUp size={16} />
            </Button>
          )}
        </div>
        {isStreaming ? (
          <p className="mt-2 flex items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 size={12} className="animate-spin" />
            Generating response...
          </p>
        ) : (
          <p className="mt-2 text-center text-xs text-muted-foreground">Enter to send · Shift+Enter for newline</p>
        )}
      </div>
    </form>
  );
}

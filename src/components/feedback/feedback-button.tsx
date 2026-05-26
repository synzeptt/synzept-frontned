"use client";

import { FormEvent, useState } from "react";
import { MessageSquarePlus, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<"issue" | "suggestion" | "memory_issue" | "support">("issue");
  const [message, setMessage] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!message.trim()) return;
    await api.sendFeedback({ feedback_type: type, message });
    setMessage("");
    setDone(true);
    setTimeout(() => {
      setDone(false);
      setOpen(false);
    }, 1200);
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-20 right-4 z-50 flex h-11 w-11 items-center justify-center rounded-full border border-border bg-surface-raised text-muted shadow-panel transition hover:text-stone-950 md:bottom-5"
        aria-label="Send feedback"
        title="Send feedback"
      >
        <MessageSquarePlus className="h-5 w-5" />
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-end bg-stone-900/20 p-4 backdrop-blur-sm md:items-end">
          <form
            onSubmit={submit}
            className="w-full max-w-sm rounded-2xl border border-border bg-surface-raised p-4 shadow-panel"
          >
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-medium text-stone-950">Feedback</p>
              <button type="button" onClick={() => setOpen(false)} className="rounded-lg p-1 text-muted hover:text-stone-950">
                <X className="h-4 w-4" />
              </button>
            </div>
            <select
              value={type}
              onChange={(event) => setType(event.target.value as typeof type)}
              className="mb-3 h-9 w-full rounded-lg border border-border bg-surface px-3 text-sm text-stone-950"
            >
              <option value="issue">Report issue</option>
              <option value="suggestion">Suggest improvement</option>
              <option value="memory_issue">Flag memory behavior</option>
              <option value="support">Ask for help</option>
            </select>
            <Textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="What should we know?"
              className="min-h-24"
            />
            <Button type="submit" className="mt-3 w-full" disabled={!message.trim()}>
              <Send className="mr-1.5 h-4 w-4" />
              {done ? "Sent" : "Send"}
            </Button>
          </form>
        </div>
      )}
    </>
  );
}


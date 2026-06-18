"use client";

import { FormEvent, useState } from "react";
import { usePathname } from "next/navigation";
import { Loader2, MessageSquarePlus, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";

export function FeedbackButton() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<"bug" | "feature_request" | "improvement" | "general" | "user_interview">("feature_request");
  const [message, setMessage] = useState("");
  const [confusing, setConfusing] = useState("");
  const [useful, setUseful] = useState("");
  const [again, setAgain] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const interview = type === "user_interview";
    const finalMessage = interview
      ? [
          `What confused you? ${confusing.trim() || "No answer"}`,
          `What was useful? ${useful.trim() || "No answer"}`,
          `Would you use this again? ${again.trim() || "No answer"}`,
        ].join("\n\n")
      : message.trim();
    if (!finalMessage.trim()) return;
    setSending(true);
    setError(null);
    try {
      await api.sendFeedback({
        feedback_type: type,
        message: finalMessage,
        metadata: interview ? { pathname, confused: confusing, useful, use_again: again } : { pathname },
      });
      void api.trackEvent("feedback_submitted", "feedback", { feedback_type: type, pathname });
      setMessage("");
      setConfusing("");
      setUseful("");
      setAgain("");
      setDone(true);
      setTimeout(() => {
        setDone(false);
        setOpen(false);
      }, 1200);
    } catch {
      setError("Feedback could not send. Keep this open and try again in a moment.");
    } finally {
      setSending(false);
    }
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
              <option value="feature_request">Feature request</option>
              <option value="user_interview">User interview</option>
              <option value="bug">Bug report</option>
              <option value="improvement">Improvement</option>
              <option value="general">General feedback</option>
            </select>
            {type === "user_interview" ? (
              <div className="space-y-2">
                <Textarea value={confusing} onChange={(event) => setConfusing(event.target.value)} placeholder="What confused you?" className="min-h-20" />
                <Textarea value={useful} onChange={(event) => setUseful(event.target.value)} placeholder="What was useful?" className="min-h-20" />
                <Textarea value={again} onChange={(event) => setAgain(event.target.value)} placeholder="Would you use this again?" className="min-h-20" />
              </div>
            ) : (
              <Textarea
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="What should we know?"
                className="min-h-24"
              />
            )}
            {error && <p className="mt-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
            <Button type="submit" className="mt-3 w-full" disabled={(type === "user_interview" ? !confusing.trim() && !useful.trim() && !again.trim() : !message.trim()) || sending}>
              {sending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Send className="mr-1.5 h-4 w-4" />}
              {done ? "Sent" : "Send"}
            </Button>
          </form>
        </div>
      )}
    </>
  );
}

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { executeWorkflowFromRequest } from "@/lib/ai-workflows";

export type QuickChatProps = {
  prompts: string[];
  onPromptSelect?: (prompt: string) => void;
};

export function QuickChat({ prompts, onPromptSelect }: QuickChatProps) {
  const router = useRouter();
  const [draft, setDraft] = useState("");

  const submit = async (value?: string) => {
    const nextPrompt = (value || draft).trim();
    if (!nextPrompt) return;
    void executeWorkflowFromRequest(nextPrompt).catch(() => undefined);
    if (onPromptSelect) {
      onPromptSelect(nextPrompt);
      return;
    }
    localStorage.setItem("synzept_chat_draft", nextPrompt);
    router.push("/chat");
  };

  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Quick chat</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">Ask Synzept anything</h2>
      </div>
      <div className="mt-6 space-y-4">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
          className="space-y-3"
        >
          <Input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask Synzept anything..."
            aria-label="Quick chat question"
          />
          <button type="submit" className="inline-flex h-10 items-center rounded-xl bg-stone-950 px-4 text-sm font-medium text-white transition hover:bg-stone-800">
            Open in chat
          </button>
        </form>
        <div className="grid gap-3 sm:grid-cols-2">
          {prompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => { void submit(prompt); }}
              className="rounded-2xl border border-stone-200 bg-stone-50 px-4 py-3 text-left text-sm text-stone-700 transition hover:bg-stone-100"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

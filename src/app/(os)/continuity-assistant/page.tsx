"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { ArrowRight, CheckCircle2, Clock3, Loader2, RotateCcw, Sparkles, Undo2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ContinuityAssistantSnapshot } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";

export default function ContinuityAssistantPage() {
  const router = useRouter();
  const [snapshot, setSnapshot] = useState<ContinuityAssistantSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSnapshot(await api.getContinuityAssistantV2());
    } catch {
      setError("Continuity Assistant could not load. Chat and Home still work.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      setSnapshot(await api.refreshContinuityAssistant());
    } catch {
      setError("Continuity Assistant could not refresh.");
    } finally {
      setRefreshing(false);
    }
  };

  const continueWorking = () => {
    if (!snapshot) return;
    localStorage.setItem(CHAT_DRAFT_KEY, buildContinuePrompt(snapshot));
    void api.trackEvent("continuity_assistant_continue_clicked", "continuity_assistant");
    router.push("/chat");
  };

  return (
    <PageFrame
      eyebrow="Continuity"
      title="Assistant"
      action={
        <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing}>
          {refreshing ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <RotateCcw className="mr-1.5 h-4 w-4" />}
          {refreshing ? "Refreshing" : "Refresh"}
        </Button>
      }
    >
      <div className="min-h-full bg-[#f7f6f2] text-stone-950">
        <div className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
          <RecoveryBanner message={error} onRetry={load} className="mb-5" />

          {loading ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <Skeleton className="h-48 rounded-lg lg:col-span-2" />
              <Skeleton className="h-40 rounded-lg" />
              <Skeleton className="h-40 rounded-lg" />
            </div>
          ) : snapshot ? (
            <div className="space-y-4 sm:space-y-5">
              <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-[0_18px_48px_rgba(32,31,28,0.07)] sm:p-6">
                <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 text-stone-400">
                      <Sparkles className="h-4 w-4" />
                      <p className="text-xs font-medium uppercase tracking-[0.14em]">Recommended Next Step</p>
                    </div>
                    <h1 className="mt-3 max-w-3xl text-2xl font-semibold leading-tight text-stone-950 sm:text-3xl">
                      {text(snapshot.recommendedNextStep.title, "Define the next action to keep momentum.")}
                    </h1>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-stone-600">
                      {text(snapshot.recommendedNextStep.reason || snapshot.recommendedNextStep.detail, "Synzept will use your recent context, open loops, and priorities to resume cleanly.")}
                    </p>
                  </div>
                  <Button onClick={continueWorking} className="h-11 shrink-0">
                    Continue
                    <ArrowRight className="ml-1.5 h-4 w-4" />
                  </Button>
                </div>
              </section>

              <div className="grid gap-4 lg:grid-cols-2">
                <ListSection icon={<Clock3 className="h-4 w-4" />} title="What Changed" items={snapshot.whatChanged} empty="No meaningful changes since your last active thread." />
                <ListSection icon={<Sparkles className="h-4 w-4" />} title="What Matters" items={snapshot.whatMatters} empty="Add a mission, goal, or project focus to sharpen this view." />
                <ListSection icon={<Undo2 className="h-4 w-4" />} title="Open Loops" items={snapshot.openLoops} empty="No open loops need attention right now." />
                <ListSection icon={<CheckCircle2 className="h-4 w-4" />} title="Recent Progress" items={snapshot.recentProgress} empty="Recent progress will appear after tasks, notes, conversations, or projects move." />
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </PageFrame>
  );
}

function ListSection({ icon, title, items, empty }: { icon: ReactNode; title: string; items: Array<Record<string, unknown>>; empty: string }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-[0_12px_34px_rgba(32,31,28,0.05)] sm:p-5">
      <div className="flex items-center gap-2 text-stone-400">
        {icon}
        <h2 className="text-xs font-medium uppercase tracking-[0.14em]">{title}</h2>
      </div>
      <div className="mt-4 space-y-2">
        {items.slice(0, 5).map((item, index) => (
          <div key={`${title}-${index}`} className="rounded-lg border border-stone-100 bg-[#fbfbf8] px-3 py-3">
            <p className="line-clamp-2 text-sm font-semibold leading-5 text-stone-950">{text(item.title || item.summary || item.name, "Untitled")}</p>
            {text(item.detail || item.description || item.reason || item.nextStep) ? (
              <p className="mt-1 line-clamp-3 text-xs leading-5 text-stone-500">{text(item.detail || item.description || item.reason || item.nextStep)}</p>
            ) : null}
          </div>
        ))}
        {!items.length ? <p className="rounded-lg border border-dashed border-stone-300 bg-[#fbfbf8] px-3 py-3 text-sm text-stone-500">{empty}</p> : null}
      </div>
    </section>
  );
}

function buildContinuePrompt(snapshot: ContinuityAssistantSnapshot) {
  return [
    "Continue from my Continuity Assistant.",
    "",
    `Recommended next step: ${text(snapshot.recommendedNextStep.title, "Continue the current focus.")}`,
    `Reason: ${text(snapshot.recommendedNextStep.reason || snapshot.recommendedNextStep.detail)}`,
    `What changed: ${snapshot.whatChanged.map((item) => text(item.title || item.summary)).filter(Boolean).join("; ") || "Nothing major"}`,
    `What matters: ${snapshot.whatMatters.map((item) => text(item.title || item.summary)).filter(Boolean).join("; ") || "No explicit priorities"}`,
    `Open loops: ${snapshot.openLoops.map((item) => text(item.title || item.summary)).filter(Boolean).join("; ") || "None visible"}`,
    "",
    "Do not ask me to re-explain. Help me continue from this context.",
  ].filter(Boolean).join("\n");
}

function text(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

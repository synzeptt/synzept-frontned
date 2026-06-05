"use client";

import { useEffect, useState } from "react";
import { RotateCcw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ContinuityAssistantSnapshot } from "@/lib/api";

function text(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function ListSection({ title, items, empty }: { title: string; items: Array<Record<string, unknown>>; empty: string }) {
  return (
    <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
      <h2 className="text-sm font-medium text-stone-950">{title}</h2>
      <div className="mt-3 space-y-2">
        {items.map((item, index) => (
          <div key={`${title}-${index}`} className="rounded-md bg-stone-50 px-3 py-2">
            <p className="text-sm font-medium text-stone-950">{text(item.title, "Untitled")}</p>
            {text(item.detail || item.description || item.reason) && (
              <p className="mt-2 text-sm leading-6 text-stone-600">{text(item.detail || item.description || item.reason)}</p>
            )}
          </div>
        ))}
        {!items.length && <p className="text-sm text-muted">{empty}</p>}
      </div>
    </section>
  );
}

export default function ContinuityAssistantPage() {
  const [snapshot, setSnapshot] = useState<ContinuityAssistantSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getContinuityAssistantV2()
      .then(setSnapshot)
      .catch(() => setError("Continuity Assistant could not load."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

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

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 md:py-10">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <Sparkles className="mt-1 h-6 w-6 text-stone-900" />
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Phase 7</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Continuity Assistant</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
                Return to what changed, what matters, what is unfinished, and what should happen next.
              </p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing}>
            <RotateCcw className="mr-1.5 h-4 w-4" />
            {refreshing ? "Refreshing" : "Refresh"}
          </Button>
        </header>

        <RecoveryBanner message={error} onRetry={load} />

        {loading ? (
          <Skeleton className="h-64 rounded-md" />
        ) : snapshot ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5 lg:col-span-2">
              <h2 className="text-sm font-medium text-stone-950">Recommended Next Step</h2>
              <p className="mt-3 text-xl font-semibold text-stone-950">{text(snapshot.recommendedNextStep.title, "Define the next action to keep momentum.")}</p>
              <p className="mt-2 text-sm leading-6 text-stone-600">{text(snapshot.recommendedNextStep.reason)}</p>
            </section>
            <ListSection title="What Changed" items={snapshot.whatChanged} empty="No meaningful changes yet." />
            <ListSection title="What Matters" items={snapshot.whatMatters} empty="No important context yet." />
            <ListSection title="Open Loops" items={snapshot.openLoops} empty="No open loops detected." />
            <ListSection title="Recent Progress" items={snapshot.recentProgress} empty="No recent progress detected." />
          </div>
        ) : null}
      </div>
    </div>
  );
}

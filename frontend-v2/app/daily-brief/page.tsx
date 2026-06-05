"use client";

import { useEffect, useState } from "react";
import { CalendarDays, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type DailyBriefSnapshot } from "@/lib/api";

function text(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function BriefList({ items, empty }: { items: Array<Record<string, unknown>>; empty: string }) {
  return (
    <div className="mt-3 space-y-2">
      {items.map((item, index) => (
        <div key={`${text(item.title, "item")}-${index}`} className="rounded-md bg-stone-50 px-3 py-2">
          <p className="text-sm font-medium text-stone-950">{text(item.title, "Untitled")}</p>
          {text(item.detail || item.description || item.reason) && (
            <p className="mt-2 text-sm leading-6 text-stone-600">{text(item.detail || item.description || item.reason)}</p>
          )}
        </div>
      ))}
      {!items.length && <p className="text-sm text-muted">{empty}</p>}
    </div>
  );
}

export default function DailyBriefPage() {
  const [brief, setBrief] = useState<DailyBriefSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getDailyBriefV2()
      .then(setBrief)
      .catch(() => setError("Daily Brief could not load."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const refresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      setBrief(await api.refreshDailyBriefV2());
    } catch {
      setError("Daily Brief could not refresh.");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 md:py-10">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <CalendarDays className="mt-1 h-6 w-6 text-stone-900" />
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Phase 8</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Daily Brief</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
                Today&apos;s continuity view, powered by the Context Engine.
              </p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing}>
            <RefreshCw className="mr-1.5 h-4 w-4" />
            {refreshing ? "Refreshing" : "Refresh"}
          </Button>
        </header>

        <RecoveryBanner message={error} onRetry={load} />

        {loading ? (
          <Skeleton className="h-64 rounded-md" />
        ) : brief ? (
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5 lg:col-span-2">
              <h2 className="text-sm font-medium text-stone-950">Recommended Next Step</h2>
              <p className="mt-3 text-xl font-semibold text-stone-950">{text(brief.recommendedNextStep.title, "Define the next action to keep momentum.")}</p>
              <p className="mt-2 text-sm leading-6 text-stone-600">{text(brief.recommendedNextStep.reason)}</p>
            </section>
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">What Matters Today</h2>
              <BriefList items={brief.whatMattersToday} empty="No priority context yet." />
            </section>
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Open Loops</h2>
              <BriefList items={brief.openLoops} empty="No open loops detected." />
            </section>
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Recent Progress</h2>
              <BriefList items={brief.recentProgress} empty="No recent progress detected." />
            </section>
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Context To Remember</h2>
              <BriefList items={brief.contextToRemember} empty="No important context yet." />
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}

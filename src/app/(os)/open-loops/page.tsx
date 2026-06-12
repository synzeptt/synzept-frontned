"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import Link from "next/link";
import {
  Archive,
  Check,
  FolderKanban,
  Pause,
  RefreshCw,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProGate } from "@/components/pro/pro-gate";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type OpenLoopEngineItem } from "@/lib/api";
import { sampleOpenLoops } from "@/lib/sample-data";
import { PageFrame } from "@frontend/components/layout/page-frame";

const typeLabels: Record<OpenLoopEngineItem["type"], string> = {
  unfinished_task: "Unfinished Task",
  pending_decision: "Pending Decision",
  waiting_response: "Waiting Response",
  blocked_work: "Blocked Work",
  follow_up: "Follow-Up",
  incomplete_idea: "Incomplete Idea",
};

export default function OpenLoopsPage() {
  const [items, setItems] = useState<OpenLoopEngineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, startRefresh] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .getOpenLoopsEngine()
      .then((data) => setItems(data.items))
      .catch(() => setError("Open Loops could not load. Your workspace is still safe."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    void api.trackEvent("open_loops_viewed", "open_loops");
  }, []);

  const activeItems = items.filter((item) => item.status === "open");
  const displayItems = activeItems.length ? activeItems : sampleOpenLoops;
  const summary = useMemo(() => summarize(displayItems), [displayItems]);
  const showingSamples = !activeItems.length;

  const refresh = () => {
    startRefresh(() => {
      void load();
    });
  };

  const act = async (item: OpenLoopEngineItem, action: "complete" | "snooze" | "ignore") => {
    setError(null);
    try {
      const updated =
        action === "complete"
          ? await api.completeOpenLoopEngineItem(item.source, item.sourceId)
          : action === "snooze"
            ? await api.snoozeOpenLoopEngineItem(item.source, item.sourceId)
            : await api.ignoreOpenLoopEngineItem(item.source, item.sourceId);
      setItems((current) => current.map((candidate) => (candidate.id === item.id ? updated : candidate)));
    } catch {
      setError("Open loop could not be updated.");
    }
  };

  return (
    <PageFrame
      eyebrow="Synzept Pro"
      title="Open Loops"
      action={
        <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing || loading}>
          <RefreshCw className={`mr-1.5 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      }
    >
      <ProGate feature="Open Loops Tracking" description="Open Loops is a Synzept Pro engine that finds unfinished work, pending decisions, blockers, follow-ups, and incomplete ideas across your workspace.">
      <div className="mx-auto max-w-6xl space-y-4 p-4 pb-24 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {loading ? (
          <OpenLoopsSkeleton />
        ) : (
          <>
            <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
              <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                <div>
                  <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
                    <RotateCcw className="h-3.5 w-3.5" />
                    What am I forgetting?
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold leading-8">Synzept remembers unfinished work so you do not have to.</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-300">
                    Review unresolved tasks, decisions, waiting items, blockers, follow-ups, and incomplete ideas across projects.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:w-[420px]">
                  <LoopStat label="Open" value={summary.total} />
                  <LoopStat label="High" value={summary.highPriority} />
                  <LoopStat label="Decisions" value={summary.pendingDecisions} />
                  <LoopStat label="Blocked" value={summary.blockedWork} />
                </div>
              </div>
            </section>

            <section className="overflow-hidden rounded-lg border border-border bg-white shadow-soft">
              <div className="border-b border-border px-4 py-3">
                <p className="text-sm font-semibold text-stone-950">Unfinished Work</p>
                <p className="mt-1 text-xs text-muted-foreground">Nothing closes automatically. You decide what is complete, snoozed, or ignored.</p>
              </div>
              <div className="divide-y divide-border">
                {displayItems.map((item) => (
                  <OpenLoopRow key={item.id} item={item} onAction={act} sample={showingSamples} />
                ))}
              </div>
            </section>
          </>
        )}
      </div>
      </ProGate>
    </PageFrame>
  );
}

function OpenLoopRow({
  item,
  onAction,
  sample = false,
}: {
  item: OpenLoopEngineItem;
  onAction: (item: OpenLoopEngineItem, action: "complete" | "snooze" | "ignore") => void;
  sample?: boolean;
}) {
  return (
    <article className="grid gap-3 px-4 py-4 md:grid-cols-[minmax(0,1.2fr)_160px_120px_110px_110px_190px] md:items-center">
      <div className="min-w-0">
        <Link href={item.href} className="line-clamp-2 text-sm font-semibold text-stone-950 hover:underline">
          {item.title}
        </Link>
        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.description || item.nextStep}</p>
      </div>
      <MetaCell icon={<FolderKanban className="h-3.5 w-3.5" />} value={item.projectName} />
      <Pill value={typeLabels[item.type]} tone={item.type === "blocked_work" ? "amber" : item.type === "pending_decision" ? "stone" : "neutral"} />
      <Pill value={item.status} tone="green" />
      <Pill value={item.priority} tone={item.priority === "high" ? "amber" : "neutral"} />
      <div className="text-xs text-muted-foreground md:text-right">
        <p>{sample ? "Example loop" : `Created ${formatDate(item.createdAt)}`}</p>
        {sample ? (
          <Link href="/projects" className="mt-2 inline-flex rounded-md border border-border px-2 py-1 text-stone-700 hover:bg-stone-50">
            Create project
          </Link>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2 md:justify-end">
            <button className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-stone-700 hover:bg-stone-50" onClick={() => onAction(item, "complete")}>
              <Check className="h-3.5 w-3.5" />
              Complete
            </button>
            <button className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-stone-700 hover:bg-stone-50" onClick={() => onAction(item, "snooze")}>
              <Pause className="h-3.5 w-3.5" />
              Snooze
            </button>
            <button className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-stone-700 hover:bg-stone-50" onClick={() => onAction(item, "ignore")}>
              <Archive className="h-3.5 w-3.5" />
              Ignore
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

function MetaCell({ icon, value }: { icon: React.ReactNode; value: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-stone-700">
      {icon}
      <span className="line-clamp-1">{value}</span>
    </div>
  );
}

function Pill({ value, tone }: { value: string; tone: "neutral" | "amber" | "green" | "stone" }) {
  const classes = {
    neutral: "bg-stone-50 text-stone-700",
    amber: "bg-amber-50 text-amber-800",
    green: "bg-emerald-50 text-emerald-800",
    stone: "bg-stone-900 text-white",
  };
  return <span className={`inline-flex w-fit rounded-md px-2 py-1 text-xs capitalize ${classes[tone]}`}>{value.replace(/_/g, " ")}</span>;
}

function LoopStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 px-3 py-3">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs text-stone-400">{label}</p>
    </div>
  );
}

function summarize(items: OpenLoopEngineItem[]) {
  const open = items.filter((item) => item.status === "open");
  return {
    total: open.length,
    highPriority: open.filter((item) => item.priority === "high").length,
    pendingDecisions: open.filter((item) => item.type === "pending_decision").length,
    blockedWork: open.filter((item) => item.type === "blocked_work").length,
  };
}

function OpenLoopsSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-40 rounded-lg" />
      <Skeleton className="h-96 rounded-lg" />
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

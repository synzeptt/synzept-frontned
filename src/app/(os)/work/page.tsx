"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  AlertCircle,
  Clock3,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { api, type ActionExecution } from "@/lib/api";
import { cn } from "@/lib/cn";
import Link from "next/link";
import { Page, PageHeader, Section, SectionHeader, Status, Metadata } from "@/components/design-system/workspace-primitives";

function getStatusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-5 w-5 text-green-600" />;
    case "failed":
    case "cancelled":
      return <AlertCircle className="h-5 w-5 text-red-600" />;
    case "executing":
    case "running":
    case "planning":
    case "queued":
      return <Loader2 className="h-5 w-5 animate-spin text-stone-600" />;
    default:
      return <Clock3 className="h-5 w-5 text-stone-400" />;
  }
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    completed: "Completed",
    failed: "Failed",
    cancelled: "Cancelled",
    executing: "Running",
    running: "Running",
    planning: "Planning",
    queued: "Queued",
    awaiting_confirmation: "Awaiting confirmation",
    waiting_approval: "Waiting for approval",
  };
  return labels[status] || status;
}

function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function WorkPage() {
  const [executions, setExecutions] = useState<ActionExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadExecutions = useCallback(async () => {
    try {
      const rows = await api.listActionExecutions();
      setExecutions(rows);
    } catch {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadExecutions();
  }, [loadExecutions]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => void loadExecutions(), 5000);
    return () => clearInterval(interval);
  }, [loadExecutions]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadExecutions();
    setRefreshing(false);
  };

  const grouped = useMemo(() => {
    const active = executions.filter((e) =>
      ["queued", "planning", "executing", "running", "awaiting_confirmation", "waiting_approval"].includes(e.status)
    );
    const completed = executions.filter((e) =>
      ["completed", "failed", "cancelled"].includes(e.status)
    );
    const needsYou = executions.filter((e) =>
      ["awaiting_confirmation", "waiting_approval"].includes(e.status)
    );

    return {
      active: active.filter((execution) => !["awaiting_confirmation", "waiting_approval"].includes(execution.status)).sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ),
      completed: completed.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      ),
      needsYou: needsYou.sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      ),
    };
  }, [executions]);

  return (
    <Page>
      <div className="mx-auto max-w-5xl px-5 py-10 sm:px-10 sm:py-16 lg:px-16">
        {/* Header */}
        <div className="mb-14 flex items-end justify-between gap-6">
          <PageHeader eyebrow="Think" title="Work" description="A quiet record of what Synzept is doing, what it needs, and what it has finished." />
          <button
            onClick={() => void handleRefresh()}
            disabled={refreshing}
            className="grid h-9 w-9 place-items-center text-stone-500 transition-colors hover:text-stone-950 disabled:opacity-50"
            aria-label="Refresh"
          >
            <RefreshCw
              className={cn("h-5 w-5 text-stone-600", {
                "animate-spin": refreshing,
              })}
            />
          </button>
        </div>

        {grouped.needsYou.length > 0 && (
          <WorkSection title="Needs you" description="A decision is waiting before Synzept can continue." tone="amber">
            {grouped.needsYou.map((execution) => <WorkCard key={execution.id} execution={execution} />)}
          </WorkSection>
        )}

        {grouped.active.length > 0 && (
          <WorkSection title="Happening now" description="Synzept is moving this work forward." tone="green">
            {grouped.active.map((execution) => <WorkCard key={execution.id} execution={execution} />)}
          </WorkSection>
        )}

        {/* Completed work */}
        {grouped.completed.length > 0 && (
          <WorkSection title="Finished" description="Completed work stays here so you can return to the result." tone="neutral">
            {grouped.completed.map((execution) => <WorkCard key={execution.id} execution={execution} />)}
          </WorkSection>
        )}

        {/* Empty state */}
        {loading ? (
          <div className="text-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-stone-400 mx-auto mb-4" />
            <p className="text-stone-600">Loading work...</p>
          </div>
        ) : executions.length === 0 ? (
          <div className="border-y border-border/10 py-12 text-center">
            <p className="text-stone-600">No work yet</p>
            <p className="text-sm text-stone-500 mt-1">
              Head to Home and tell Synzept what to do
            </p>
          </div>
        ) : null}
      </div>
    </Page>
  );
}

function WorkSection({ title, description, tone, children }: { title: string; description: string; tone: "amber" | "green" | "neutral"; children: React.ReactNode }) {
  return <Section className="mb-12"><SectionHeader title={title} description={description} /><div className="divide-y divide-border/10">{children}</div></Section>;
}

function WorkCard({ execution }: { execution: ActionExecution }) {
  const terminal = execution.status === "completed";
  return <Link href={`/actions/${execution.id}`} className="group block py-5 transition hover:bg-surface-overlay/40"><div className="flex items-start gap-4"><div className="mt-0.5">{getStatusIcon(execution.status)}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-start justify-between gap-2"><p className="font-medium text-stone-900 group-hover:text-stone-950">{execution.title}</p><Status tone={execution.status === "completed" ? "success" : execution.status === "failed" ? "error" : "neutral"}>{getStatusLabel(execution.status)}</Status></div><Metadata>{getTimeAgo(execution.updated_at)}</Metadata>{!terminal && !["awaiting_confirmation", "waiting_approval"].includes(execution.status) && <div className="mt-3 h-1 overflow-hidden bg-stone-200"><div className="h-full bg-emerald-700 transition-all" style={{ width: `${Math.min(execution.progress, 100)}%` }} /></div>}{terminal && execution.output && <p className="mt-3 line-clamp-2 text-sm leading-6 text-stone-600">{execution.output}</p>}{execution.error && <p className="mt-3 text-sm leading-6 text-red-700">{execution.error}</p>}<p className="mt-3 text-xs font-semibold text-emerald-800">{terminal ? "Review result" : "Open Work"} <span aria-hidden="true">→</span></p></div></div></Link>;
}

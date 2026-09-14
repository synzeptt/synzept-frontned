"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, CheckCircle2, Clock3, Search, Sparkles, XCircle } from "lucide-react";
import { WorkspacePage } from "@/components/layout/workspace-content";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ActionExecution } from "@/lib/api";

const examplePrompts = [
  "Research competitors and summarize the top three",
  "Map the customer onboarding experience",
  "Evaluate the latest product feedback themes",
];

const statusLabels: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  waiting_approval: "Waiting for approval",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
};

export default function ResearchHistoryPage() {
  const [executions, setExecutions] = useState<ActionExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const load = async () => {
      setError(null);
      try {
        const rows = await api.listActionExecutions();
        setExecutions(rows.filter((execution) => execution.action_type === "research"));
      } catch {
        setError("Research history could not load. Please try again in a moment.");
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, []);

  const researchExecutions = useMemo(() => executions, [executions]);

  const filteredExecutions = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return researchExecutions;
    return researchExecutions.filter((execution) => {
      return (
        execution.title.toLowerCase().includes(normalized) ||
        execution.request.toLowerCase().includes(normalized) ||
        (execution.output ?? "").toLowerCase().includes(normalized)
      );
    });
  }, [query, researchExecutions]);

  const activeExecutions = useMemo(() => filteredExecutions.filter((item) => ["queued", "running", "waiting_approval"].includes(item.status)), [filteredExecutions]);
  const completedExecutions = useMemo(() => filteredExecutions.filter((item) => item.status === "completed"), [filteredExecutions]);
  const failedExecutions = useMemo(() => filteredExecutions.filter((item) => item.status === "failed"), [filteredExecutions]);

  const latestCompleted = useMemo(
    () => [...completedExecutions].sort((a, b) => dateValue(b.updated_at) - dateValue(a.updated_at)).slice(0, 4),
    [completedExecutions],
  );

  return (
    <div className="min-h-full bg-[#faf9f6] text-stone-950">
      <WorkspacePage className="!max-w-[1050px] !pb-24 !pt-10 sm:!pt-14">
        <header className="pb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#54705c]">Research</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-stone-950">Research history</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-600">Review completed reports, follow along with active research, and reopen saved findings from past research work.</p>
        </header>

        <RecoveryBanner message={error} onRetry={() => window.location.reload()} />

        {!loading && !error && researchExecutions.length === 0 ? (
          <section className="mb-6 rounded-[28px] border border-dashed border-stone-200 bg-stone-50 px-6 py-5 text-sm text-stone-600">
            No saved research reports yet. Start a new research request from the workspace and it will appear here automatically.
          </section>
        ) : null}

        <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
          <div className="grid gap-3 md:grid-cols-[1fr_0.7fr]">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#54705c]">Search research</p>
              <p className="mt-2 text-sm leading-7 text-stone-600">Filter across past research requests, summaries, and outcomes.</p>
            </div>
            <label className="relative block">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search research reports"
                className="h-12 w-full rounded-3xl border border-stone-200 bg-stone-50 px-11 text-sm text-stone-900 outline-none transition focus:border-[#78907f] focus:ring-2 focus:ring-[#78907f]/20"
              />
            </label>
          </div>
        </section>

        <section className="mt-6 grid gap-4 sm:grid-cols-3">
          <StatCard label="Total reports" value={String(researchExecutions.length)} description="All research executions created by Synzept." />
          <StatCard label="Active" value={String(activeExecutions.length)} description="Research still in progress or waiting for your review." />
          <StatCard label="Completed" value={String(completedExecutions.length)} description="Research work that is ready to reuse." />
        </section>

        <div className="mt-6 space-y-6">
        <section className="rounded-[32px] border border-[#dce5de] bg-[#f7fbf8] p-6 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#54705c]">Continuity layer</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-950">Your research now builds on previous reports</h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-600">Finished reports surface shared context, related topics, and a clear path to continue where the last study left off.</p>
            </div>
            <div className="rounded-2xl border border-[#dce5de] bg-white px-4 py-3 text-sm text-stone-700">
              <span className="font-semibold text-stone-950">{completedExecutions.length > 0 ? "Memory-aware" : "Fresh start"}</span>
              <div className="mt-1">{completedExecutions.length > 0 ? "Previous reports are being linked in the workspace." : "Start the first report to create your first memory trail."}</div>
            </div>
          </div>
        </section>
          <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#54705c]">Saved workspace</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-950">Completed research reports</h2>
              </div>
              <Link href="/actions" className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-stone-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-stone-800">
                Open work <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="mt-6 grid gap-4">
              {loading ? (
                Array.from({ length: 2 }).map((_, index) => <Skeleton key={index} className="h-28 rounded-3xl" />)
              ) : completedExecutions.length === 0 ? (
                <div className="rounded-[28px] border border-dashed border-stone-200 bg-stone-50 px-6 py-12 text-center text-sm text-stone-500">
                  No completed research yet. Start a new research request from the home page and the report will arrive here.
                </div>
              ) : (
                latestCompleted.map((execution) => <ResearchCard key={execution.id} execution={execution} />)
              )}
            </div>
          </section>

          <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#54705c]">In progress</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-950">Active research</h2>
              </div>
              <div className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">{activeExecutions.length} active</div>
            </div>
            <div className="mt-6 space-y-4">
              {loading ? (
                Array.from({ length: 2 }).map((_, index) => <Skeleton key={index} className="h-28 rounded-3xl" />)
              ) : activeExecutions.length === 0 ? (
                <div className="rounded-[28px] border border-dashed border-stone-200 bg-stone-50 px-6 py-12 text-center text-sm text-stone-500">
                  No active research right now. Create a new research report from home to start collecting findings.
                </div>
              ) : (
                activeExecutions.map((execution) => <ResearchCard key={execution.id} execution={execution} />)
              )}
            </div>
          </section>

          {failedExecutions.length ? (
            <section className="rounded-[32px] border border-red-200 bg-red-50 p-6 shadow-sm">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-red-700">Recovery</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-950">Research that needs attention</h2>
              <div className="mt-6 space-y-4">
                {failedExecutions.map((execution) => (
                  <ResearchCard key={execution.id} execution={execution} highlight="failed" />
                ))}
              </div>
            </section>
          ) : null}

          <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#54705c]">Explore more</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-950">What to research next</h2>
              </div>
              <Link href="/home" className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50">
                Back to home <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {examplePrompts.map((prompt) => (
                <Link key={prompt} href="/home" className="rounded-[24px] border border-stone-200 bg-stone-50 px-4 py-4 text-sm font-medium text-stone-700 transition hover:border-stone-300">
                  {prompt}
                </Link>
              ))}
            </div>
          </section>
        </div>
      </WorkspacePage>
    </div>
  );
}

function StatCard({ label, value, description }: { label: string; value: string; description: string }) {
  return (
    <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">{label}</p>
      <p className="mt-4 text-3xl font-semibold text-stone-950">{value}</p>
      <p className="mt-2 text-sm text-stone-500">{description}</p>
    </div>
  );
}

function ResearchCard({ execution, highlight }: { execution: ActionExecution; highlight?: "failed" }) {
  const status = statusLabels[execution.status] ?? execution.status;
  const updated = formatRelativeTime(execution.updated_at);
  const metadata = execution.metadata as Record<string, unknown> | undefined;
  const memoryTopics = Array.isArray(metadata?.research_memory_topics) ? metadata.research_memory_topics.filter((entry): entry is string => typeof entry === "string") : [];
  const relatedResearchCount = Array.isArray(metadata?.research_memory_context) ? metadata.research_memory_context.length : 0;
  const confidence = typeof metadata?.research_memory_confidence === "number" ? metadata.research_memory_confidence : null;
  return (
    <Link href={`/actions/${execution.id}`} className={`block rounded-[28px] border ${highlight === "failed" ? "border-red-200 bg-red-50" : "border-stone-200 bg-[#fcfdfc]"} p-5 transition hover:border-stone-300`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-stone-500">{status}</p>
          <h3 className="mt-2 text-xl font-semibold text-stone-950">{execution.title}</h3>
          <p className="mt-2 text-sm leading-7 text-stone-600">{execution.request}</p>
        </div>
        <div className="space-y-3 text-sm text-stone-600">
          <div className="rounded-2xl border border-stone-200 bg-white px-3 py-2">
            <p className="font-semibold text-stone-900">Progress</p>
            <p className="mt-1">{execution.progress}%</p>
          </div>
          <div className="rounded-2xl border border-stone-200 bg-white px-3 py-2">
            <p className="font-semibold text-stone-900">Updated</p>
            <p className="mt-1">{updated}</p>
          </div>
        </div>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-100">
        <div className={`h-full rounded-full ${highlight === "failed" ? "bg-red-500" : "bg-[#78907f]"}`} style={{ width: `${execution.progress}%` }} />
      </div>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-stone-500">
        <span>{execution.output ? `${execution.output.slice(0, 100).replace(/\s+/g, " ")}…` : "No report available yet."}</span>
        <div className="flex flex-wrap items-center gap-2">
          {relatedResearchCount > 0 ? (
            <span className="rounded-full border border-[#dce5de] bg-[#f7fbf8] px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-[#54705c]">{relatedResearchCount} related</span>
          ) : null}
          {memoryTopics.length ? <span className="rounded-full border border-stone-200 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">{memoryTopics[0]}</span> : null}
          <span className="inline-flex items-center gap-1 font-semibold text-stone-900">Open <ArrowRight className="h-3.5 w-3.5" /></span>
        </div>
      </div>
      {confidence !== null ? (
        <div className="mt-3 flex items-center gap-2">
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-stone-100">
            <div className="h-full rounded-full bg-[#58705f]" style={{ width: `${Math.round(confidence * 100)}%` }} />
          </div>
          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">Memory {Math.round(confidence * 100)}%</span>
        </div>
      ) : null}
    </Link>
  );
}

function dateValue(value: string | null | undefined) {
  if (!value) return 0;
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? timestamp : 0;
}

function formatRelativeTime(value: string | null | undefined) {
  if (!value) return "recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  const diff = Date.now() - date.getTime();
  const minutes = Math.max(1, Math.floor(diff / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1_440) return `${Math.floor(minutes / 60)}h ago`;
  return `${Math.floor(minutes / 1_440)}d ago`;
}

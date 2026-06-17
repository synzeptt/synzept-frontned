"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, CircleDot, Sparkles, Target, TriangleAlert } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type AutonomousWorkspace, type IntelligenceItem } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

export default function AutonomousWorkspacePage() {
  const [workspace, setWorkspace] = useState<AutonomousWorkspace | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setError(null);
    return api
      .getAutonomousWorkspace()
      .then(setWorkspace)
      .catch(() => setError("Execution context could not refresh."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const refreshSuggestions = () => {
    setRefreshing(true);
    api
      .generateAutonomousSuggestions()
      .then((suggestions) => setWorkspace((current) => current ? { ...current, suggestions } : current))
      .then(load)
      .catch(() => setError("Suggestions could not refresh."))
      .finally(() => setRefreshing(false));
  };

  return (
    <PageFrame eyebrow="Execution" title="Autonomous Workspace">
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {loading && !workspace ? (
          <div className="space-y-5">
            <Skeleton className="h-48 rounded-lg" />
            <Skeleton className="h-72 rounded-lg" />
          </div>
        ) : (
          <>
            <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
              <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                <div>
                  <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-stone-400">
                    <Target className="h-3.5 w-3.5" />
                    Weekly priority focus
                  </p>
                  <h1 className="mt-3 text-3xl font-semibold leading-9">{workspace?.weekly_plan.priority_focus || "Create one goal plan to generate weekly focus."}</h1>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300">Synzept turns goals into planned work, tracks completion and blockers, and proposes the next useful action from live workspace context.</p>
                </div>
                <button
                  type="button"
                  onClick={refreshSuggestions}
                  disabled={refreshing}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-4 text-sm font-medium text-stone-950 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Sparkles className="h-4 w-4" />
                  {refreshing ? "Refreshing" : "Refresh Suggestions"}
                </button>
              </div>
            </section>

            <section className="grid gap-5 lg:grid-cols-3">
              <MetricCard label="Planned" value={workspace?.execution.planned.length || 0} icon={CircleDot} />
              <MetricCard label="Completed" value={workspace?.execution.completed.length || 0} icon={CheckCircle2} />
              <MetricCard label="Blocked" value={workspace?.execution.blocked.length || 0} icon={TriangleAlert} />
            </section>

            <section className="grid gap-5 lg:grid-cols-2">
              <PlanColumn title="This Week" items={workspace?.weekly_plan.this_week || []} empty="Create or update a goal to generate this week's plan." />
              <PlanColumn title="Next Week" items={workspace?.weekly_plan.next_week || []} empty="Next week's queue appears after this week's focus is structured." />
            </section>

            <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
              <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
                <SectionTitle title="Project Health" />
                <div className="mt-3 space-y-2">
                  {(workspace?.project_health || []).slice(0, 8).map((project) => (
                    <Link key={project.project_id} href={`/projects/${project.project_id}`} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="line-clamp-1 text-sm font-medium text-stone-950">{project.project_title}</p>
                          <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">{project.reasons[0] || "Health is calculated from progress, risk, and momentum."}</p>
                        </div>
                        <span className="shrink-0 text-sm font-semibold text-stone-800">{Math.round(project.health_score)}%</span>
                      </div>
                    </Link>
                  ))}
                  {!workspace?.project_health.length && <p className="text-sm leading-6 text-muted-foreground">Project health appears once active projects have execution signals.</p>}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
                <SectionTitle title="Autonomous Suggestions" />
                <div className="mt-3 space-y-2">
                  {(workspace?.suggestions || []).slice(0, 8).map((item) => (
                    <Link key={item.id} href={item.project_id ? `/projects/${item.project_id}` : "/dashboard"} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
                      <p className="line-clamp-2 text-sm font-medium text-stone-950">{item.title}</p>
                      <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
                    </Link>
                  ))}
                  {!workspace?.suggestions.length && <p className="text-sm leading-6 text-muted-foreground">Synzept will propose actions as goals, projects, decisions, and activity connect.</p>}
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </PageFrame>
  );
}

function MetricCard({ label, value, icon: Icon }: { label: string; value: number; icon: typeof CircleDot }) {
  return (
    <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <Icon className="h-4 w-4 text-stone-500" />
      </div>
      <p className="mt-2 text-3xl font-semibold text-stone-950">{value}</p>
    </div>
  );
}

function PlanColumn({ title, items, empty }: { title: string; items: IntelligenceItem[]; empty: string }) {
  return (
    <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <SectionTitle title={title} />
      <div className="mt-3 space-y-2">
        {items.slice(0, 6).map((item) => (
          <Link key={`${item.type}-${item.title}`} href={item.project_id ? `/projects/${item.project_id}` : "/tasks"} className="group flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <div className="min-w-0">
              <p className="line-clamp-2 text-sm font-medium text-stone-950">{item.title}</p>
              <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
            </div>
            <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-stone-400 transition group-hover:translate-x-0.5 group-hover:text-stone-900" />
          </Link>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <p className="text-sm font-semibold text-stone-950">{title}</p>;
}

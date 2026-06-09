"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, FolderKanban, ListTodo, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ContinuityAssistant, type Dashboard, type Task } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

const doneStatuses = new Set(["completed", "archived", "done"]);

export default function DailyBriefPage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [assistant, setAssistant] = useState<ContinuityAssistant | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, startRefresh] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([
      api.getDashboard(),
      api.getContinuityAssistant().catch(() => null),
    ])
      .then(([dashboardData, assistantData]) => {
        setDashboard(dashboardData);
        setAssistant(assistantData);
      })
      .catch(() => setError("Daily Brief could not load. Your workspace is still safe."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const tasks = useMemo(() => dashboard?.unfinished_tasks || dashboard?.priorities || dashboard?.tasks || [], [dashboard]);
  const openTasks = useMemo(() => tasks.filter((task) => !doneStatuses.has(task.status)), [tasks]);
  const whatMatters = uniqueItems([
    ...(dashboard?.daily?.focus_areas || []),
    ...(dashboard?.focus_areas || []),
    ...(assistant?.priorities || []),
    ...(dashboard?.projects || []).filter((project) => project.currentFocus).slice(0, 3).map((project) => `${project.name}: ${project.currentFocus}`),
  ]);
  const projectAttention = (dashboard?.projects || [])
    .filter((project) => !doneStatuses.has(project.status) && (!project.currentFocus?.trim() || !project.recommendedNextStep?.trim()))
    .slice(0, 5);
  const openLoops = uniqueItems([
    ...(assistant?.open_loops || []),
    ...(dashboard?.daily?.carry_forward || []),
    ...openTasks.slice(0, 5).map((task) => task.title),
  ]);
  const recentProgress = uniqueItems([
    ...(assistant?.recent_progress || []),
    ...(dashboard?.daily?.completed_today || []),
    ...(dashboard?.recent_activity || []).map((item) => item.title),
  ]);
  const nextStep = getRecommendedNextStep(dashboard, assistant, openTasks);

  const refresh = () => {
    startRefresh(() => {
      void load();
    });
  };

  return (
    <PageFrame
      eyebrow="Daily Brief"
      title="Today"
      action={
        <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing || loading}>
          <RefreshCw className="mr-1.5 h-4 w-4" />
          Refresh
        </Button>
      }
    >
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {loading ? (
          <BriefSkeleton />
        ) : (
          <>
            <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
              <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
                <div>
                  <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
                    <CalendarDays className="h-3.5 w-3.5" />
                    Recommended next step
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold leading-8">{nextStep.title}</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-300">{nextStep.reason}</p>
                </div>
                <Link href={nextStep.href} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-stone-950 transition hover:bg-stone-100">
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </section>

            <section className="grid gap-5 lg:grid-cols-2">
              <BriefList title="What Matters Today" items={whatMatters.slice(0, 6)} empty="Add a project focus or task to create today's brief." />
              <BriefList title="Open Loops" items={openLoops.slice(0, 6)} empty="No open loops need attention right now." />
              <ProjectAttentionList projects={projectAttention} />
              <BriefList title="Recent Progress" items={recentProgress.slice(0, 6)} empty="Recent progress will appear after tasks, projects, notes, or conversations change." />
            </section>
          </>
        )}
      </div>
    </PageFrame>
  );
}

function ProjectAttentionList({ projects }: { projects: NonNullable<Dashboard["projects"]> }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
        <FolderKanban className="h-4 w-4 text-muted" />
        Projects Needing Attention
      </p>
      <div className="mt-3 space-y-2">
        {projects.map((project) => (
          <Link key={project.id} href={`/projects/${project.id}`} className="block rounded-md bg-stone-50 px-3 py-3 text-sm transition hover:bg-stone-100">
            <p className="font-medium text-stone-900">{project.name}</p>
            <p className="mt-1 text-xs text-muted-foreground">{!project.currentFocus?.trim() ? "Needs current focus" : "Needs recommended next step"}</p>
          </Link>
        ))}
        {!projects.length && <p className="text-sm leading-6 text-muted-foreground">Active projects have clear anchors.</p>}
      </div>
    </section>
  );
}

function BriefList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
        <ListTodo className="h-4 w-4 text-muted" />
        {title}
      </p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <p key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-5 text-stone-800">{item}</p>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </section>
  );
}

function getRecommendedNextStep(dashboard: Dashboard | null, assistant: ContinuityAssistant | null, tasks: Task[]) {
  const project = dashboard?.projects?.find((item) => item.recommendedNextStep?.trim()) || dashboard?.projects?.find((item) => item.currentFocus?.trim());
  const task = tasks[0];
  if (project) {
    return {
      title: project.recommendedNextStep || project.currentFocus || project.name,
      reason: `This keeps ${project.name} moving and creates a clear return point for later.`,
      href: `/projects/${project.id}`,
    };
  }
  if (assistant?.recommendation.title) {
    return {
      title: assistant.recommendation.title,
      reason: assistant.recommendation.reason || assistant.recommendation.detail,
      href: "/dashboard",
    };
  }
  if (task) {
    return {
      title: task.title,
      reason: "This is the clearest unfinished task in your workspace.",
      href: "/tasks",
    };
  }
  return {
    title: "Create one project anchor",
    reason: "A current focus and next step give Synzept something useful to restore tomorrow.",
    href: "/projects",
  };
}

function BriefSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-44 rounded-lg" />
      <div className="grid gap-5 lg:grid-cols-2">
        <Skeleton className="h-48 rounded-lg" />
        <Skeleton className="h-48 rounded-lg" />
      </div>
    </div>
  );
}

function uniqueItems(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

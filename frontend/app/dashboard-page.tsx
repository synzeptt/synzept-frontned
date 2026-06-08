"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import Link from "next/link";
import { ArrowRight, CircleDot, MessageSquare, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ContinuityAssistant, type ContinuityCard, type Conversation, type Dashboard, type Project, type Task } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";

const doneStatuses = new Set(["completed", "archived", "done"]);
const priorityRank: Record<string, number> = { high: 3, medium: 2, low: 1 };

export function DashboardPage() {
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const [, startTransition] = useTransition();
  const [assistant, setAssistant] = useState<ContinuityAssistant | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .getDashboard()
      .then((data) => startTransition(() => setDashboard(data)))
      .catch(() => setError("Dashboard context could not refresh. Your workspace is still safe."))
      .finally(() => setLoading(false));
  }, [setDashboard, setLoading, startTransition]);

  useEffect(() => {
    if (dashboard && hasFreshDashboard()) return;
    load();
  }, [dashboard, hasFreshDashboard, load]);

  useEffect(() => {
    api.getContinuityAssistant().then(setAssistant).catch(() => setAssistant(null));
  }, []);

  useEffect(() => {
    if (!dashboard) return;
    void api.trackEvent(dashboard.returning_user?.is_returning ? "returning_dashboard_loaded" : "dashboard_loaded", "dashboard", {
      cards: dashboard.continuity_cards?.length ?? 0,
      open_tasks: dashboard.stats?.open_tasks ?? 0,
      active_projects: dashboard.stats?.active_projects ?? 0,
    });
  }, [dashboard]);

  const tasks = useMemo(() => dashboard?.unfinished_tasks || dashboard?.priorities || dashboard?.tasks || [], [dashboard]);
  const priorityTasks = useMemo(() => getPriorityTasks(tasks), [tasks]);
  const continuityItems = useMemo(() => getContinuityItems(dashboard, priorityTasks), [dashboard, priorityTasks]);
  const focusAreas = useMemo(() => dashboard?.daily?.focus_areas || dashboard?.focus_areas || [], [dashboard]);
  const command = useMemo(
    () => getContinuityCommand({ dashboard, assistant, priorityTasks, continuityItems, focusAreas }),
    [assistant, continuityItems, dashboard, focusAreas, priorityTasks],
  );
  const openLoops = useMemo(() => getOpenLoops({ dashboard, assistant, priorityTasks, continuityItems }), [assistant, continuityItems, dashboard, priorityTasks]);
  const recentProgress = useMemo(() => getRecentProgress({ dashboard, assistant, continuityItems }), [assistant, continuityItems, dashboard]);

  return (
    <PageFrame eyebrow="Continuity" title="Home">
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {isLoading && !dashboard ? (
          <DashboardSkeleton />
        ) : (
          <>
            <FocusPanel command={command} returningSummary={dashboard?.returning_user?.summary || dashboard?.returning_user?.prompt} />
            <section className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)]">
              <ContinuityPanel items={continuityItems} />
              <div className="space-y-5">
                <CompactList title="Open Loops" items={openLoops} empty="No unfinished loop needs attention right now." />
                <CompactList title="Recent Progress" items={recentProgress} empty="Recent progress will appear as you complete work." />
              </div>
            </section>
            <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
              <ProjectList projects={dashboard?.projects || []} />
              <PriorityTasks tasks={priorityTasks} />
            </section>
            <ConversationList conversations={dashboard?.recent_conversations || []} />
          </>
        )}
      </div>
    </PageFrame>
  );
}

function FocusPanel({ command, returningSummary }: { command: ReturnType<typeof getContinuityCommand>; returningSummary?: string }) {
  return (
    <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.72fr)_auto] lg:items-center">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
            <Target className="h-3.5 w-3.5" />
            Current focus
          </p>
          <h2 className="mt-2 line-clamp-2 text-2xl font-semibold leading-8">{command.focusTitle}</h2>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-300">{command.focusDetail}</p>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/5 p-4">
          <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
            <ArrowRight className="h-3.5 w-3.5" />
            Recommended next step
          </p>
          <p className="mt-2 line-clamp-2 text-base font-semibold">{command.nextTitle}</p>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-300">{command.nextDetail}</p>
        </div>
        <div className="lg:w-44">
          <Link
            href={command.href}
            onClick={() => api.trackEvent("continuity_command_opened", "dashboard", { target: command.href, source: command.source })}
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-stone-950 transition hover:bg-stone-100"
          >
            {command.actionLabel}
            <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="mt-2 text-xs leading-5 text-stone-400">{returningSummary || "Start here, then work from one clear next step."}</p>
        </div>
      </div>
    </section>
  );
}

function ContinuityPanel({ items }: { items: ContinuityCard[] }) {
  const lead = items[0];
  const rest = items.slice(1, 4);

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <SectionHeading title="Where You Left Off" description="Return points with enough context to resume without re-reading everything." />
      {lead ? (
        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(240px,0.72fr)]">
          <Link href={lead.href} onClick={() => trackContinuationOpen(lead, "lead")} className="group rounded-lg border border-stone-200 bg-stone-50 p-5 transition hover:bg-white">
            <div className="flex items-center justify-between gap-3">
              <Badge variant={lead.priority === "high" ? "accent" : "muted"}>{labelForType(lead.type)}</Badge>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-stone-900" />
            </div>
            <h3 className="mt-4 text-xl font-semibold leading-7 text-stone-950">{lead.title}</h3>
            <p className="mt-2 line-clamp-3 text-sm leading-6 text-muted-foreground">{lead.description}</p>
            {lead.reason && <p className="mt-3 text-xs text-stone-500">{lead.reason}</p>}
          </Link>
          <div className="space-y-2">
            {rest.map((item) => (
              <ResumeRow key={`${item.type}-${item.id}`} item={item} />
            ))}
            {!rest.length && <p className="rounded-md bg-stone-50 px-3 py-3 text-sm text-muted-foreground">Create one more project, task, note, or conversation to add another return point.</p>}
          </div>
        </div>
      ) : (
        <div className="mt-4 rounded-lg border border-dashed border-stone-200 bg-stone-50 p-4">
          <p className="text-sm font-medium text-stone-950">Create one return point.</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">Start with a project or task. Synzept will use it to show what matters when you come back.</p>
        </div>
      )}
    </section>
  );
}

function ResumeRow({ item }: { item: ContinuityCard }) {
  return (
    <Link href={item.href} onClick={() => trackContinuationOpen(item, "supporting")} className="group flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
      <div className="min-w-0">
        <p className="line-clamp-1 text-sm font-medium text-stone-900">{item.title}</p>
        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.continuation_prompt || item.description}</p>
      </div>
      <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-stone-400 transition group-hover:translate-x-0.5 group-hover:text-stone-900" />
    </Link>
  );
}

function CompactList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <SectionHeading title={title} />
      <div className="mt-3 space-y-2">
        {items.slice(0, 5).map((item) => (
          <p key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-5 text-stone-800">{item}</p>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </section>
  );
}

function ProjectList({ projects }: { projects: Project[] }) {
  const active = projects.filter((project) => !doneStatuses.has(project.status)).slice(0, 4);

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <SectionHeading title="Projects" description="Active work with visible focus and next step." />
      <div className="mt-3 space-y-2">
        {active.map((project) => (
          <Link key={project.id} href={`/projects/${project.id}`} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="line-clamp-1 text-sm font-medium text-stone-950">{project.name}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                  {project.currentFocus || project.recommendedNextStep || project.description || "Add a focus and next step."}
                </p>
              </div>
              <ProjectHealth project={project} />
            </div>
          </Link>
        ))}
        {!active.length && <p className="text-sm leading-6 text-muted-foreground">No active projects yet. Create one to anchor your workspace.</p>}
      </div>
    </section>
  );
}

function ProjectHealth({ project }: { project: Project }) {
  const ready = Boolean(project.currentFocus?.trim() && project.recommendedNextStep?.trim());
  return (
    <span className={cn("shrink-0 rounded-md px-2 py-1 text-xs", ready ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800")}>
      {ready ? "Ready" : "Needs anchor"}
    </span>
  );
}

function PriorityTasks({ tasks }: { tasks: Task[] }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <SectionHeading title="Priority Tasks" />
      <div className="mt-3 space-y-2">
        {tasks.slice(0, 5).map((task) => (
          <Link key={task.id} href="/tasks" className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <div className="flex items-start gap-3">
              <CircleDot className="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
              <div className="min-w-0">
                <p className="line-clamp-2 text-sm font-medium text-stone-900">{task.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{task.due_at ? dueLabel(task.due_at) : task.priority || task.status}</p>
              </div>
            </div>
          </Link>
        ))}
        {!tasks.length && <p className="text-sm leading-6 text-muted-foreground">No priority task is pulling focus right now.</p>}
      </div>
    </section>
  );
}

function ConversationList({ conversations }: { conversations: Conversation[] }) {
  if (!conversations.length) return null;

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <SectionHeading title="Recent Conversations" description="Threads that are safe to reopen because context is preserved." />
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {conversations.slice(0, 4).map((conversation) => (
          <Link key={conversation.id} href={`/chat?conversation=${conversation.id}`} className="group rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="line-clamp-1 text-sm font-medium text-stone-900">{conversation.title || "Untitled conversation"}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{conversation.summary || "Open this thread to continue."}</p>
              </div>
              <MessageSquare className="h-4 w-4 shrink-0 text-stone-400 transition group-hover:text-stone-900" />
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

function SectionHeading({ title, description }: { title: string; description?: string }) {
  return (
    <div>
      <p className="text-sm font-semibold text-stone-950">{title}</p>
      {description && <p className="mt-1 text-sm leading-6 text-muted-foreground">{description}</p>}
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-52 rounded-lg" />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)]">
        <Skeleton className="h-72 rounded-lg" />
        <Skeleton className="h-72 rounded-lg" />
      </div>
    </div>
  );
}

function getContinuityItems(dashboard: Dashboard | null, tasks: Task[]): ContinuityCard[] {
  const existing = dashboard?.continuity_cards || [];
  if (existing.length) return existing;

  const projectCards: ContinuityCard[] = (dashboard?.projects || []).slice(0, 3).map((project) => ({
    id: project.id,
    type: "project",
    title: project.name,
    description: project.currentFocus || project.context_summary || project.description || "Active project context is ready.",
    action_label: "Open project",
    href: `/projects/${project.id}`,
    project_id: project.id,
    task_id: null,
    conversation_id: null,
    priority: project.currentFocus && project.recommendedNextStep ? "high" : "medium",
    updated_at: project.updatedAt || project.createdAt || project.created_at || null,
  }));

  const taskCards: ContinuityCard[] = tasks.slice(0, 3).map((task) => ({
    id: task.id,
    type: "task",
    title: task.title,
    description: task.description || dueLabel(task.due_at) || "Open task ready to continue.",
    action_label: "Open task",
    href: "/tasks",
    project_id: task.project_id,
    task_id: task.id,
    conversation_id: null,
    priority: task.priority || "medium",
    updated_at: task.created_at,
  }));

  const conversationCards: ContinuityCard[] = (dashboard?.recent_conversations || []).slice(0, 2).map((conversation) => ({
    id: conversation.id,
    type: "conversation",
    title: conversation.title || "Untitled conversation",
    description: conversation.summary || "Recent thread ready to pick back up.",
    action_label: "Open conversation",
    href: `/chat?conversation=${conversation.id}`,
    project_id: conversation.project_id,
    task_id: null,
    conversation_id: conversation.id,
    priority: "medium",
    updated_at: conversation.updated_at || conversation.created_at || null,
  }));

  return [...projectCards, ...taskCards, ...conversationCards];
}

function getContinuityCommand({
  dashboard,
  assistant,
  priorityTasks,
  continuityItems,
  focusAreas,
}: {
  dashboard: Dashboard | null;
  assistant: ContinuityAssistant | null;
  priorityTasks: Task[];
  continuityItems: ContinuityCard[];
  focusAreas: string[];
}) {
  const leadProject = dashboard?.projects?.find((project) => project.currentFocus || project.recommendedNextStep) || dashboard?.projects?.[0];
  const leadTask = priorityTasks[0];
  const leadContinuation = continuityItems[0];
  const focusTitle =
    focusAreas[0] ||
    leadProject?.currentFocus ||
    leadTask?.title ||
    leadContinuation?.title ||
    "Create one clear focus.";
  const focusDetail =
    leadProject?.name ||
    dashboard?.continuity_summary ||
    leadContinuation?.description ||
    "Synzept works best when one project, task, or conversation is the anchor.";
  const nextTitle =
    leadProject?.recommendedNextStep ||
    assistant?.recommendation.title ||
    leadTask?.title ||
    leadContinuation?.action_label ||
    "Add a project or task.";
  const nextDetail =
    assistant?.recommendation.detail ||
    leadContinuation?.continuation_prompt ||
    leadContinuation?.description ||
    "Add one next step so your next session starts from momentum.";
  const href =
    (leadProject?.id ? `/projects/${leadProject.id}` : "") ||
    leadContinuation?.href ||
    (leadTask ? "/tasks" : "") ||
    "/projects";

  return {
    focusTitle,
    focusDetail,
    nextTitle,
    nextDetail,
    href,
    actionLabel: leadProject ? "Open project" : leadTask ? "Open task" : "Start setup",
    source: leadProject ? "project" : leadTask ? "task" : leadContinuation?.type || "empty",
  };
}

function getOpenLoops({
  dashboard,
  assistant,
  priorityTasks,
  continuityItems,
}: {
  dashboard: Dashboard | null;
  assistant: ContinuityAssistant | null;
  priorityTasks: Task[];
  continuityItems: ContinuityCard[];
}) {
  return uniqueItems([
    ...(assistant?.open_loops || []),
    ...(dashboard?.daily?.carry_forward || []),
    ...priorityTasks.slice(0, 4).map((task) => task.title),
    ...continuityItems.filter((item) => item.type === "task").map((item) => item.title),
  ]);
}

function getRecentProgress({
  dashboard,
  assistant,
  continuityItems,
}: {
  dashboard: Dashboard | null;
  assistant: ContinuityAssistant | null;
  continuityItems: ContinuityCard[];
}) {
  return uniqueItems([
    ...(assistant?.recent_progress || []),
    ...(dashboard?.daily?.completed_today || []),
    ...(dashboard?.recent_activity || []).map((item) => item.title),
    ...continuityItems.filter((item) => item.reason).map((item) => item.reason || ""),
  ]);
}

function getPriorityTasks(tasks: Task[]) {
  return tasks
    .filter((task) => !doneStatuses.has(task.status))
    .slice()
    .sort((a, b) => {
      const aOverdue = a.due_at && new Date(a.due_at) < startOfToday() ? 1 : 0;
      const bOverdue = b.due_at && new Date(b.due_at) < startOfToday() ? 1 : 0;
      if (aOverdue !== bOverdue) return bOverdue - aOverdue;
      return (priorityRank[b.priority] || 0) - (priorityRank[a.priority] || 0);
    });
}

function trackContinuationOpen(item: ContinuityCard, placement: "lead" | "supporting") {
  void api.trackEvent("continuity_card_opened", "dashboard", {
    id: item.id,
    type: item.type,
    placement,
    project_id: item.project_id,
    task_id: item.task_id,
    conversation_id: item.conversation_id,
  });
}

function startOfToday() {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  return date;
}

function dueLabel(value: string | null) {
  if (!value) return "";
  const due = new Date(value);
  if (Number.isNaN(due.getTime())) return "";
  if (due < startOfToday()) return "Overdue";
  return `Due ${due.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
}

function labelForType(type: string) {
  if (type === "conversation") return "conversation";
  if (type === "project") return "project";
  if (type === "task") return "task";
  return type;
}

function uniqueItems(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

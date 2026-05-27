"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState, useTransition } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BriefcaseBusiness,
  CalendarDays,
  CheckCircle2,
  CircleDot,
  Clock3,
  FolderKanban,
  ListTodo,
  MessageSquare,
  NotebookText,
  Save,
  Sparkles,
} from "lucide-react";
import { Markdown } from "@/components/chat/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GuidanceCard } from "@/components/ui/guidance-card";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, type ContinuityCard, type Conversation, type DailyExperience, type Dashboard, type Memory, type Project, type RecentActivity, type Task } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";

const doneStatuses = new Set(["completed", "archived", "done"]);
const priorityRank: Record<string, number> = { high: 3, medium: 2, low: 1 };

export function DashboardPage() {
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const [, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .getDashboard()
      .then((data) => startTransition(() => setDashboard(data)))
      .catch(() => setError("Dashboard context could not refresh. Existing workspace data is still safe; retry when the connection settles."))
      .finally(() => setLoading(false));
  }, [setDashboard, setLoading, startTransition]);

  useEffect(() => {
    if (dashboard && hasFreshDashboard()) return;
    load();
  }, [dashboard, hasFreshDashboard, load]);

  useEffect(() => {
    if (!dashboard) return;
    api.trackEvent(dashboard.returning_user?.is_returning ? "returning_dashboard_loaded" : "dashboard_loaded", "dashboard", {
      cards: dashboard.continuity_cards?.length ?? 0,
      open_tasks: dashboard.stats?.open_tasks ?? 0,
      active_projects: dashboard.stats?.active_projects ?? 0,
      days_since_last_seen: dashboard.returning_user?.days_since_last_seen ?? null,
    });
  }, [dashboard]);

  const briefing = dashboard?.daily?.morning_briefing || dashboard?.morning_briefing || dashboard?.briefing;
  const focusAreas = dashboard?.daily?.focus_areas || dashboard?.focus_areas || [];
  const suggestions = dashboard?.daily?.suggestions || dashboard?.suggestions || [];
  const tasks = useMemo(() => dashboard?.unfinished_tasks || dashboard?.priorities || dashboard?.tasks || [], [dashboard]);
  const priorityTasks = useMemo(() => getPriorityTasks(tasks), [tasks]);
  const continuityItems = useMemo(() => getContinuityItems(dashboard, tasks), [dashboard, tasks]);

  return (
    <PageFrame
      eyebrow="Daily continuity"
      title="Workspace"
    >
      <div className="mx-auto max-w-7xl space-y-7 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {isLoading && !dashboard ? (
          <DashboardSkeleton />
        ) : (
          <>
            <section className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
              <ContinuitySection items={continuityItems} />
              <div className="space-y-5">
                <MemoryContextPanel
                  memories={dashboard?.memories || []}
                  continuitySummary={dashboard?.continuity_summary || ""}
                  focusAreas={focusAreas}
                />
                <DailyFocus briefing={briefing} focusAreas={focusAreas} suggestions={suggestions} />
              </div>
            </section>

            <DailyRhythm daily={dashboard?.daily || null} priorities={priorityTasks} continuationItems={continuityItems} onSaved={load} />

            <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div className="space-y-5">
                <ActiveProjects
                  projects={dashboard?.projects || []}
                  conversations={dashboard?.recent_conversations || []}
                  tasks={dashboard?.tasks || tasks}
                  recentActivity={dashboard?.recent_activity || []}
                />
                <RecentConversations conversations={dashboard?.recent_conversations || []} />
              </div>
              <div className="space-y-5">
                <PriorityTasks tasks={priorityTasks} />
              </div>
            </section>

            <section className="grid gap-5">
              <ContinuityIntelligencePanel
                stats={dashboard?.stats}
                tasks={priorityTasks}
                projects={dashboard?.projects || []}
                continuitySummary={dashboard?.continuity_summary || ""}
                recurringPriorities={dashboard?.recurring_priorities || []}
                ongoingThemes={dashboard?.ongoing_themes || []}
                timeline={dashboard?.continuity_timeline || []}
                memoryEvolution={dashboard?.memory_evolution || []}
              />
            </section>
          </>
        )}
      </div>
    </PageFrame>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
        <Skeleton className="h-80 rounded-lg" />
        <Skeleton className="h-80 rounded-lg" />
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-56 rounded-lg" />
        </div>
        <div className="space-y-5">
          <Skeleton className="h-64 rounded-lg" />
          <Skeleton className="h-56 rounded-lg" />
        </div>
      </div>
    </div>
  );
}

function ContinuitySection({ items }: { items: ContinuityCard[] }) {
  const lead = items[0];
  const supporting = items.slice(1, 5);

  return (
    <SectionShell
      icon={<Clock3 className="h-4 w-4" />}
      title="Continue where you left off"
      description="The fastest path back into recent projects, active conversations, remembered context, and open loops."
      actionHref={lead?.href}
      actionLabel={lead ? "Resume" : undefined}
    >
      {lead ? (
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.7fr)]">
          <Link href={lead.href} onClick={() => trackContinuationOpen(lead, "lead")} className="group rounded-lg border border-stone-200 bg-stone-50/80 p-5 transition hover:border-stone-300 hover:bg-white">
            <div className="flex items-center justify-between gap-3">
              <Badge variant={lead.priority === "high" ? "accent" : "muted"}>{labelForType(lead.type)}</Badge>
              <ArrowRight className="h-4 w-4 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-stone-900" />
            </div>
            <h2 className="mt-4 text-xl font-semibold leading-7 text-stone-950">{lead.title}</h2>
            <p className="mt-3 line-clamp-4 text-sm leading-6 text-muted-foreground">{lead.description}</p>
            {lead.reason && <p className="mt-3 text-xs text-stone-500">{lead.reason}</p>}
            <p className="mt-5 text-sm font-medium text-stone-900">{lead.action_label || "Continue"}</p>
          </Link>
          <div className="space-y-2">
            {supporting.map((item) => (
              <ResumeRow key={`${item.type}-${item.id}`} item={item} />
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <EmptyPanel
            title="Create one restore point"
            text="Add a project, task, note, or conversation. Synzept will turn that into a daily place to resume without reconstructing the whole story."
          />
          <div className="grid gap-2 md:grid-cols-3">
            <Link href="/projects" className="rounded-md border border-stone-200 bg-stone-50 px-3 py-3 text-sm text-stone-700 transition hover:bg-white">Create a project</Link>
            <Link href="/tasks" className="rounded-md border border-stone-200 bg-stone-50 px-3 py-3 text-sm text-stone-700 transition hover:bg-white">Add one next action</Link>
            <Link href="/chat" className="rounded-md border border-stone-200 bg-stone-50 px-3 py-3 text-sm text-stone-700 transition hover:bg-white">Start a thread</Link>
          </div>
        </div>
      )}
    </SectionShell>
  );
}

function MemoryContextPanel({
  memories,
  continuitySummary,
  focusAreas,
}: {
  memories: Memory[];
  continuitySummary: string;
  focusAreas: string[];
}) {
  const remembered = memories.slice(0, 3);
  const activeFocus = focusAreas.slice(0, 2);

  return (
    <SectionShell compact icon={<Sparkles className="h-4 w-4" />} title="Synzept remembers" description="Context that follows you across sessions.">
      <div className="space-y-3">
        {continuitySummary && (
          <div className="rounded-lg bg-stone-50 p-3">
            <p className="text-xs font-medium uppercase text-stone-500">Recent context</p>
            <p className="mt-2 line-clamp-4 text-sm leading-6 text-stone-800">{continuitySummary}</p>
          </div>
        )}
        <div className="space-y-2">
          {remembered.map((memory) => (
            <div key={memory.id} className="rounded-md border border-stone-200 bg-white px-3 py-2">
              <p className="line-clamp-2 text-sm leading-5 text-stone-900">{memory.summary || memory.content}</p>
              <p className="mt-1 text-xs text-stone-500">{memory.category || memory.memory_type || "memory"}</p>
            </div>
          ))}
          {!remembered.length && (
            <div className="rounded-md border border-stone-200 bg-white px-3 py-2">
              <p className="text-sm leading-5 text-stone-900">Synzept is ready to remember goals, decisions, and active work as you use it.</p>
            </div>
          )}
        </div>
        {!!activeFocus.length && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase text-stone-500">Active focus</p>
            <div className="space-y-1.5">
              {activeFocus.map((focus) => (
                <p key={focus} className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-800">{focus}</p>
              ))}
            </div>
          </div>
        )}
      </div>
    </SectionShell>
  );
}

function ResumeRow({ item }: { item: ContinuityCard }) {
  return (
    <Link href={item.href} onClick={() => trackContinuationOpen(item, "supporting")} className="group flex items-start justify-between gap-3 rounded-md border border-transparent bg-stone-50 px-3 py-3 transition hover:border-stone-200 hover:bg-white">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">{iconForType(item.type)}</span>
          <p className="truncate text-sm font-medium text-stone-900">{item.title}</p>
        </div>
        <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.description}</p>
        {(item.reason || item.continuation_prompt) && (
          <p className="mt-1 line-clamp-1 text-xs text-stone-500">{item.reason || item.continuation_prompt}</p>
        )}
      </div>
      <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-stone-400 transition group-hover:text-stone-900" />
    </Link>
  );
}

function ActiveProjects({
  projects,
  conversations,
  tasks,
  recentActivity,
}: {
  projects: Project[];
  conversations: Conversation[];
  tasks: Task[];
  recentActivity: RecentActivity[];
}) {
  return (
    <SectionShell icon={<FolderKanban className="h-4 w-4" />} title="Active Projects" description="Lightweight project anchors with recent movement and next-work signals." actionHref="/projects" actionLabel="Open projects">
      {!projects.length && (
        <GuidanceCard title="Why projects matter" className="mb-3">
          Projects are the easiest way to keep related notes, tasks, threads, and memory connected across days.
        </GuidanceCard>
      )}
      <div className="grid gap-3 md:grid-cols-2">
        {projects.slice(0, 4).map((project) => {
          const projectTasks = tasks.filter((task) => task.project_id === project.id);
          const done = projectTasks.filter((task) => doneStatuses.has(task.status)).length;
          const open = projectTasks.length - done;
          const linkedThreads = conversations.filter((conversation) => conversation.project_id === project.id).length;
          const activity = recentActivity.find((item) => item.project_id === project.id);
          return (
            <Link key={project.id} href={`/projects/${project.id}`} className="rounded-lg border border-stone-200 bg-white p-4 transition hover:bg-stone-50">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="truncate text-base font-semibold text-stone-950">{project.name}</h3>
                  <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">{project.context_summary || project.description || "No saved project context yet."}</p>
                </div>
                <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-stone-400" />
              </div>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
                <span className="rounded-full bg-stone-100 px-2.5 py-1">{open} open tasks</span>
                <span className="rounded-full bg-stone-100 px-2.5 py-1">{linkedThreads} linked threads</span>
              </div>
              <div className="mt-4 h-1.5 overflow-hidden rounded-full bg-stone-100">
                <div className="h-full rounded-full bg-stone-800" style={{ width: `${getProgress(done, projectTasks.length)}%` }} />
              </div>
              <p className="mt-3 line-clamp-1 text-xs text-stone-500">{activity?.title || "Ready to restore context when you return."}</p>
            </Link>
          );
        })}
        {!projects.length && <EmptyPanel title="No active projects yet" text="Projects become the calm containers for work that spans more than one sitting." className="md:col-span-2" />}
      </div>
    </SectionShell>
  );
}

function RecentConversations({ conversations }: { conversations: Conversation[] }) {
  return (
    <SectionShell icon={<MessageSquare className="h-4 w-4" />} title="Recent Conversations" description="Recent threads with enough context to re-enter without rereading everything." actionHref="/chat" actionLabel="Open chat">
      <div className="grid gap-2 md:grid-cols-2">
        {conversations.slice(0, 4).map((conversation) => (
          <Link key={conversation.id} href={`/chat?conversation=${conversation.id}`} className="group rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <div className="flex items-start justify-between gap-3">
              <p className="line-clamp-1 text-sm font-medium text-stone-900">{conversation.title || "Untitled conversation"}</p>
              <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-stone-400 group-hover:text-stone-900" />
            </div>
            <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted-foreground">{conversation.summary || "Continue this thread and Synzept will keep the context connected."}</p>
          </Link>
        ))}
        {!conversations.length && <EmptyPanel title="No recent conversations" text="Threads you return to will appear here with continuation shortcuts." className="md:col-span-2" />}
      </div>
    </SectionShell>
  );
}

function PriorityTasks({ tasks }: { tasks: Task[] }) {
  return (
    <SectionShell compact icon={<ListTodo className="h-4 w-4" />} title="Priority Tasks" description="Only the work most likely to need attention today." actionHref="/tasks" actionLabel="Open tasks">
      <div className="space-y-2">
        {tasks.slice(0, 6).map((task) => (
          <Link key={task.id} href="/tasks" className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="line-clamp-2 text-sm font-medium text-stone-900">{task.title}</p>
                <p className="mt-1 text-xs text-muted-foreground">{task.due_at ? dueLabel(task.due_at) : task.status.replace("_", " ")}</p>
              </div>
              <Badge variant={task.priority === "high" ? "accent" : "muted"}>{task.priority || "normal"}</Badge>
            </div>
          </Link>
        ))}
        {!tasks.length && <EmptyLine text="No open priority task is pulling focus right now." />}
      </div>
    </SectionShell>
  );
}

function DailyFocus({
  briefing,
  focusAreas,
  suggestions,
}: {
  briefing?: string;
  focusAreas: string[];
  suggestions: Array<{ type: string; label: string; description: string }>;
}) {
  return (
    <SectionShell compact icon={<Sparkles className="h-4 w-4" />} title="Daily Focus" description="Short guidance for what to continue and what to avoid scattering across.">
      <div className="space-y-4">
        {briefing ? (
          <div className="rounded-lg bg-stone-50 p-4 text-sm leading-6">
            <Markdown content={briefing} />
          </div>
        ) : (
          <EmptyPanel title="No daily guidance yet" text="Once Synzept has a little context, this becomes a compact recommendation for today." />
        )}
        <div className="space-y-2">
          {focusAreas.slice(0, 3).map((item) => (
            <div key={item} className="flex gap-2 rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-800">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
              <span>{item}</span>
            </div>
          ))}
        </div>
        {!!suggestions.length && (
          <div className="space-y-2">
            {suggestions.slice(0, 2).map((suggestion) => (
              <div key={`${suggestion.type}-${suggestion.label}`} className="rounded-md bg-stone-50 px-3 py-2">
                <p className="text-sm font-medium text-stone-900">{suggestion.label}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{suggestion.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </SectionShell>
  );
}

function DailyRhythm({
  daily,
  priorities,
  continuationItems,
  onSaved,
}: {
  daily: DailyExperience | null;
  priorities: Task[];
  continuationItems: ContinuityCard[];
  onSaved: () => Promise<unknown> | unknown;
}) {
  const [progress, setProgress] = useState("");
  const [completed, setCompleted] = useState("");
  const [unfinished, setUnfinished] = useState("");
  const [insights, setInsights] = useState("");
  const [tomorrow, setTomorrow] = useState("");
  const [resume, setResume] = useState("");
  const [saving, setSaving] = useState(false);
  const phase = daily?.workflow_phase || "morning";

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      await api.saveDailyWrapUp({
        progress_summary: progress.trim() || undefined,
        completed: lines(completed),
        unfinished: lines(unfinished),
        insights: lines(insights),
        tomorrow_priorities: lines(tomorrow),
        continuation_points: lines(resume),
      });
      setProgress("");
      setCompleted("");
      setUnfinished("");
      setInsights("");
      setTomorrow("");
      setResume("");
      await onSaved();
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionShell
      icon={<CalendarDays className="h-4 w-4" />}
      title="Daily Rhythm"
      description="A light operating loop for starting, restoring, and closing the day with continuity intact."
    >
      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)]">
        <div className="space-y-3">
          <div className="rounded-lg bg-stone-50 p-4">
            <Badge variant={phase === "closed" ? "accent" : "muted"}>{phase.replace("_", " ")}</Badge>
            <p className="mt-3 text-sm leading-6 text-stone-800">
              {daily?.rhythm_prompt || "Choose one priority and preserve enough context that returning later feels easy."}
            </p>
          </div>
          <RhythmList
            title="Morning startup"
            items={(daily?.focus_areas?.length ? daily.focus_areas : priorities.map((task) => task.title)).slice(0, 3)}
            empty="No focus priority yet. Capture one next action."
          />
          <RhythmList
            title="Return points"
            items={continuationItems.map((item) => item.continuation_prompt || item.title).slice(0, 3)}
            empty="Continuation cards will become your midday restore points."
          />
          <RhythmList
            title="Tomorrow prepared"
            items={(daily?.tomorrow_priorities || daily?.continuation_points || []).slice(0, 3)}
            empty="Wrap up once to preload the next session."
          />
        </div>

        <form onSubmit={save} className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
          <div>
            <p className="text-sm font-semibold text-stone-950">End-of-day wrap-up</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Preserve the thread of the day: what moved, what remains open, and where tomorrow should begin.
            </p>
          </div>
          <Textarea value={progress} onChange={(event) => setProgress(event.target.value)} placeholder="What changed today?" rows={3} />
          <div className="grid gap-3 md:grid-cols-2">
            <Textarea value={completed} onChange={(event) => setCompleted(event.target.value)} placeholder="Completed, one per line" rows={3} />
            <Textarea value={unfinished} onChange={(event) => setUnfinished(event.target.value)} placeholder="Still open, one per line" rows={3} />
            <Textarea value={tomorrow} onChange={(event) => setTomorrow(event.target.value)} placeholder="Tomorrow priorities" rows={3} />
            <Textarea value={resume} onChange={(event) => setResume(event.target.value)} placeholder="Resume from..." rows={3} />
          </div>
          <Textarea value={insights} onChange={(event) => setInsights(event.target.value)} placeholder="Insights or context worth remembering" rows={2} />
          <Button type="submit" size="sm" disabled={saving || !hasWrapUpInput(progress, completed, unfinished, insights, tomorrow, resume)}>
            <Save className="mr-1.5 h-4 w-4" />
            Save wrap-up
          </Button>
        </form>
      </div>
    </SectionShell>
  );
}

function RhythmList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase text-stone-500">{title}</p>
      <div className="space-y-1.5">
        {items.map((item) => (
          <div key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-800">
            {item}
          </div>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </div>
  );
}

function ContinuityIntelligencePanel({
  stats,
  tasks,
  projects,
  continuitySummary,
  recurringPriorities,
  ongoingThemes,
  timeline,
  memoryEvolution,
}: {
  stats?: { active_projects: number; open_tasks: number; recent_conversations: number; notes_updated: number };
  tasks: Task[];
  projects: Project[];
  continuitySummary: string;
  recurringPriorities: Array<{ label: string; summary: string; score: number; count: number }>;
  ongoingThemes: Array<{ label: string; summary: string; score: number; count: number }>;
  timeline: Array<{ date: string; headline: string; summary: string; recurring_priorities: string[]; recurring_themes: string[]; unresolved_items: string[]; continuity_score: number }>;
  memoryEvolution: string[];
}) {
  const overdue = tasks.filter((task) => task.due_at && new Date(task.due_at) < startOfToday()).length;
  const items = [
    { label: "Active projects", value: stats?.active_projects ?? projects.length },
    { label: "Open tasks", value: stats?.open_tasks ?? tasks.length },
    { label: "Overdue", value: overdue },
    { label: "Recent threads", value: stats?.recent_conversations ?? 0 },
  ];

  return (
    <SectionShell compact icon={<CalendarDays className="h-4 w-4" />} title="Continuity Intelligence" description="A quiet view of what keeps repeating, what still needs attention, and what Synzept should preserve next time.">
      <div className="space-y-4">
        {continuitySummary && (
          <div className="rounded-lg bg-stone-50 p-4">
            <p className="text-xs font-medium uppercase text-stone-500">Current continuity summary</p>
            <p className="mt-2 text-sm leading-6 text-stone-800">{continuitySummary}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          {items.map((item) => (
            <div key={item.label} className="rounded-md border border-stone-200 bg-stone-50 px-3 py-3">
              <p className="text-2xl font-semibold text-stone-950">{item.value}</p>
              <p className="mt-1 text-xs text-muted-foreground">{item.label}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <ContinuityList title="Recurring priorities" items={recurringPriorities.slice(0, 3)} empty="No repeated priority has emerged yet." />
          <ContinuityList title="Ongoing themes" items={ongoingThemes.slice(0, 3)} empty="No strong theme signal yet." />
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase text-stone-500">Continuity timeline</p>
          <div className="space-y-2">
            {timeline.slice(0, 3).map((entry) => (
              <div key={`${entry.date}-${entry.headline}`} className="rounded-md bg-stone-50 px-3 py-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-stone-900">{entry.headline}</p>
                  <p className="text-xs text-stone-500">{formatContinuityDate(entry.date)}</p>
                </div>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{entry.summary}</p>
                {!!entry.unresolved_items.length && <p className="mt-1 text-xs text-stone-500">{entry.unresolved_items.length} unresolved item{entry.unresolved_items.length === 1 ? "" : "s"} preserved.</p>}
              </div>
            ))}
            {!timeline.length && <EmptyLine text="A short continuity timeline will appear once Synzept has a few saved snapshots." />}
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase text-stone-500">Memory evolution</p>
          <div className="space-y-1.5">
            {memoryEvolution.slice(0, 3).map((item) => (
              <div key={item} className="rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-800">
                {item}
              </div>
            ))}
            {!memoryEvolution.length && <EmptyLine text="Repeated memory patterns will appear here once the continuity layer has history." />}
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function ContinuityList({ title, items, empty }: { title: string; items: Array<{ label: string; summary: string; count: number; score: number }>; empty: string }) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase text-stone-500">{title}</p>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="rounded-md border border-stone-200 bg-white px-3 py-2">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-stone-900">{item.label}</p>
              <Badge variant="muted">{item.count}x</Badge>
            </div>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.summary}</p>
          </div>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </div>
  );
}

function SectionShell({
  icon,
  title,
  description,
  actionHref,
  actionLabel,
  compact,
  children,
}: {
  icon: ReactNode;
  title: string;
  description: string;
  actionHref?: string;
  actionLabel?: string;
  compact?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={cn("rounded-lg border border-border bg-white shadow-soft", compact ? "p-4" : "p-5")}>
      <div className="mb-4 flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
            <span className="text-muted-foreground">{icon}</span>
            {title}
          </p>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
        {actionHref && actionLabel && (
          <Link href={actionHref} className="shrink-0 rounded-md px-2 py-1 text-xs font-medium text-stone-600 transition hover:bg-stone-100 hover:text-stone-950">
            {actionLabel}
          </Link>
        )}
      </div>
      {children}
    </section>
  );
}

function EmptyPanel({ title, text, className }: { title: string; text: string; className?: string }) {
  return (
    <div className={cn("rounded-lg border border-dashed border-stone-200 bg-stone-50 p-4", className)}>
      <p className="text-sm font-medium text-stone-900">{title}</p>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{text}</p>
    </div>
  );
}

function EmptyLine({ text }: { text: string }) {
  return <p className="text-sm leading-6 text-muted-foreground">{text}</p>;
}

function getContinuityItems(dashboard: Dashboard | null, tasks: Task[]): ContinuityCard[] {
  const existing = dashboard?.continuity_cards || [];
  if (existing.length) return existing;

  const taskCards: ContinuityCard[] = tasks.slice(0, 3).map((task) => ({
    id: task.id,
    type: "task",
    title: task.title,
    description: task.description || dueLabel(task.due_at) || "Open task ready to continue.",
    action_label: "Continue task",
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
    action_label: "Reopen conversation",
    href: `/chat?conversation=${conversation.id}`,
    project_id: conversation.project_id,
    task_id: null,
    conversation_id: conversation.id,
    priority: "medium",
    updated_at: conversation.updated_at || conversation.created_at || null,
  }));

  const projectCards: ContinuityCard[] = (dashboard?.projects || []).slice(0, 2).map((project) => ({
    id: project.id,
    type: "project",
    title: project.name,
    description: project.context_summary || project.description || "Active project context is ready to restore.",
    action_label: "Open project",
    href: `/projects/${project.id}`,
    project_id: project.id,
    task_id: null,
    conversation_id: null,
    priority: "medium",
    updated_at: project.created_at,
  }));

  const noteCards: ContinuityCard[] = (dashboard?.notes || []).slice(0, 2).map((note) => ({
    id: note.id,
    type: "note",
    title: note.title || "Recent note",
    description: note.summary || note.content || "Saved context ready to revisit.",
    action_label: "Open notes",
    href: "/notes",
    project_id: note.project_id,
    task_id: null,
    conversation_id: null,
    priority: "medium",
    updated_at: note.created_at,
  }));

  const memoryCards: ContinuityCard[] = (dashboard?.memories || []).slice(0, 2).map((memory) => ({
    id: memory.id,
    type: "memory",
    title: "Synzept remembers",
    description: memory.summary || memory.content || "A piece of context Synzept can carry forward.",
    action_label: "Review memory",
    href: "/settings",
    project_id: memory.project_id ?? null,
    task_id: null,
    conversation_id: null,
    priority: "medium",
    updated_at: memory.created_at,
  }));

  return [...conversationCards, ...projectCards, ...noteCards, ...memoryCards, ...taskCards];
}

function trackContinuationOpen(item: ContinuityCard, placement: "lead" | "supporting") {
  api.trackEvent("continuity_card_opened", "dashboard", {
    id: item.id,
    type: item.type,
    placement,
    score: item.continuity_score ?? 0,
    priority: item.priority,
    project_id: item.project_id,
    task_id: item.task_id,
    conversation_id: item.conversation_id,
  });
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

function getProgress(done: number, total: number) {
  if (!total) return 8;
  return Math.max(8, Math.round((done / total) * 100));
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

function formatContinuityDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function lines(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function hasWrapUpInput(...values: string[]) {
  return values.some((value) => value.trim().length > 0);
}

function labelForType(type: string) {
  if (type === "conversation") return "conversation";
  if (type === "project") return "project";
  if (type === "task") return "task";
  return type;
}

function iconForType(type: string) {
  if (type === "conversation") return <MessageSquare className="h-4 w-4" />;
  if (type === "project") return <FolderKanban className="h-4 w-4" />;
  if (type === "task") return <CircleDot className="h-4 w-4" />;
  if (type === "note") return <NotebookText className="h-4 w-4" />;
  if (type === "memory") return <Sparkles className="h-4 w-4" />;
  return <BriefcaseBusiness className="h-4 w-4" />;
}

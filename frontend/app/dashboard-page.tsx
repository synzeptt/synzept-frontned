"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState, useTransition } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpenCheck,
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
  Target,
  UserRound,
} from "lucide-react";
import { Markdown } from "@/components/chat/markdown";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GuidanceCard } from "@/components/ui/guidance-card";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, type ContinuityAssistant, type ContinuityCard, type Conversation, type DailyExperience, type Dashboard, type Memory, type Project, type ProactiveOverview, type RecentActivity, type Task, type Workspace, type WorkspaceSearchResult } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";
import { dailyBriefApi } from "../../frontend-v2/lib/daily-brief";
import { learningEngineApi } from "../../frontend-v2/lib/learning-engine";
import type { DailyBrief } from "../../frontend-v2/types/daily-brief";
import type { LearningEngine } from "../../frontend-v2/types/learning-engine";

const doneStatuses = new Set(["completed", "archived", "done"]);
const priorityRank: Record<string, number> = { high: 3, medium: 2, low: 1 };

export function DashboardPage() {
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const [, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [proactive, setProactive] = useState<ProactiveOverview | null>(null);
  const [assistant, setAssistant] = useState<ContinuityAssistant | null>(null);
  const [dailyBrief, setDailyBrief] = useState<DailyBrief | null>(null);
  const [learning, setLearning] = useState<LearningEngine | null>(null);

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
    Promise.all([
      api.getWorkspace().then(setWorkspace).catch(() => setWorkspace(null)),
      api.getProactiveOverview().then(setProactive).catch(() => setProactive(null)),
      api.getContinuityAssistant().then(setAssistant).catch(() => setAssistant(null)),
      dailyBriefApi.today().then(setDailyBrief).catch(() => setDailyBrief(null)),
      learningEngineApi.get().then(setLearning).catch(() => setLearning(null)),
    ]);
  }, []);

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
  const focusAreas = useMemo(() => dashboard?.daily?.focus_areas || dashboard?.focus_areas || [], [dashboard]);
  const suggestions = dashboard?.daily?.suggestions || dashboard?.suggestions || [];
  const tasks = useMemo(() => dashboard?.unfinished_tasks || dashboard?.priorities || dashboard?.tasks || [], [dashboard]);
  const priorityTasks = useMemo(() => getPriorityTasks(tasks), [tasks]);
  const continuityItems = useMemo(() => getContinuityItems(dashboard, tasks), [dashboard, tasks]);
  const continuityCommand = useMemo(
    () => getContinuityCommand({ dashboard, workspace, assistant, dailyBrief, priorityTasks, continuityItems, focusAreas }),
    [dashboard, workspace, assistant, dailyBrief, priorityTasks, continuityItems, focusAreas],
  );

  return (
    <PageFrame
      eyebrow="Daily continuity"
      title="Home"
    >
      <div className="mx-auto max-w-7xl space-y-7 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {isLoading && !dashboard ? (
          <DashboardSkeleton />
        ) : (
          <>
            <ContinuityCommandPanel command={continuityCommand} returningUser={dashboard?.returning_user} />
            <MissionControlOverview
              dashboard={dashboard}
              assistant={assistant}
              dailyBrief={dailyBrief}
              priorityTasks={priorityTasks}
              continuityItems={continuityItems}
              focusAreas={focusAreas}
              command={continuityCommand}
            />
            <section className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.55fr)]">
              <ContinuitySection items={continuityItems} returningUser={dashboard?.returning_user} />
              <div className="space-y-5">
                <DailyFocus briefing={briefing} focusAreas={focusAreas} suggestions={suggestions} />
                <PriorityTasks tasks={priorityTasks} />
              </div>
            </section>

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
                <MemoryContextPanel
                  memories={dashboard?.memories || []}
                  continuitySummary={dashboard?.continuity_summary || ""}
                  focusAreas={focusAreas}
                />
                <ContinuityAssistantPanel assistant={assistant} />
              </div>
            </section>

            <DailyRhythm daily={dashboard?.daily || null} dailyBrief={dailyBrief} learning={learning} assistant={assistant} priorities={priorityTasks} continuationItems={continuityItems} onSaved={load} onLearningAnalyzed={setLearning} />

            {!dashboard?.projects?.length && (
              <V2JourneyPanel
                dashboard={dashboard}
                workspace={workspace}
                assistant={assistant}
                dailyBrief={dailyBrief}
                learning={learning}
                continuityItems={continuityItems}
              />
            )}

            <WorkspaceOverviewPanel workspace={workspace} />
            <ProactiveIntelligencePanel overview={proactive} />

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

function MissionControlOverview({
  dashboard,
  assistant,
  dailyBrief,
  priorityTasks,
  continuityItems,
  focusAreas,
  command,
}: {
  dashboard: Dashboard | null;
  assistant: ContinuityAssistant | null;
  dailyBrief: DailyBrief | null;
  priorityTasks: Task[];
  continuityItems: ContinuityCard[];
  focusAreas: string[];
  command: ReturnType<typeof getContinuityCommand>;
}) {
  const activeProjects = dashboard?.projects?.filter((project) => !doneStatuses.has(project.status)) || [];
  const openTasks = priorityTasks.filter((task) => !doneStatuses.has(task.status));
  const assistantLoops = assistant?.open_loops || [];
  const dailyLoops = dailyBrief?.open_loops || [];
  const openLoopItems = uniqueItems([
    ...assistantLoops,
    ...dailyLoops,
    ...openTasks.slice(0, 3).map((task) => task.title),
    ...continuityItems.filter((item) => item.type === "task" || item.type === "project").map((item) => item.title),
  ]);
  const recentChanges = getRecentChanges(dashboard, assistant, dailyBrief, continuityItems);
  const completedToday = dashboard?.daily?.completed_today?.length || dailyBrief?.context.recent_progress?.length || 0;
  const progressTotal = Math.max(completedToday + openLoopItems.length, activeProjects.length, 1);
  const progressValue = getProgress(completedToday, progressTotal);
  const returningSummary = dashboard?.returning_user?.is_returning
    ? dashboard.returning_user.summary || dashboard.returning_user.prompt
    : "This is your current operating picture.";

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="grid gap-5 xl:grid-cols-[minmax(0,0.82fr)_minmax(0,1.18fr)]">
        <div className="space-y-4">
          <div>
            <p className="text-xs font-medium uppercase text-stone-500">Mission control</p>
            <h2 className="mt-2 text-2xl font-semibold leading-8 text-stone-950">Resume with context already loaded.</h2>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{returningSummary}</p>
          </div>
          <div className="rounded-lg bg-stone-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-medium uppercase text-stone-500">Progress visibility</p>
              <p className="text-sm font-semibold text-stone-950">{progressValue}%</p>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-stone-200">
              <div className="h-full rounded-full bg-stone-950" style={{ width: `${progressValue}%` }} />
            </div>
            <p className="mt-3 text-sm leading-6 text-stone-700">
              {completedToday
                ? `${completedToday} progress item${completedToday === 1 ? "" : "s"} captured against ${openLoopItems.length} open loop${openLoopItems.length === 1 ? "" : "s"}.`
                : `${openLoopItems.length} open loop${openLoopItems.length === 1 ? "" : "s"} still need a clear finish line.`}
            </p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2">
          <MissionSignal label="Current focus" value={command.focusTitle} detail={command.focusDetail} href={command.href} action="Open focus" />
          <MissionSignal label="Recommended next step" value={command.nextTitle} detail={command.nextDetail} href={command.href} action={command.actionLabel} dark />
          <MissionList title="Open loops" items={openLoopItems.slice(0, 4)} empty="No unfinished loop is pulling attention right now." href="/tasks" />
          <MissionList title="What changed" items={recentChanges.slice(0, 4)} empty="Recent progress will appear after projects, notes, tasks, or conversations change." href="/timeline" />
          <MissionList title="Today's anchors" items={uniqueItems(focusAreas).slice(0, 4)} empty="Add one project focus or daily brief to create today's anchor." href="/daily-brief" />
          <MissionList title="Return points" items={continuityItems.map((item) => item.continuation_prompt || item.title).slice(0, 4)} empty="Start a project, task, note, or chat to create a return point." href="/projects" />
        </div>
      </div>
    </section>
  );
}

function MissionSignal({
  label,
  value,
  detail,
  href,
  action,
  dark,
}: {
  label: string;
  value: string;
  detail: string;
  href: string;
  action: string;
  dark?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "group min-h-48 rounded-lg border p-4 transition",
        dark
          ? "border-stone-900 bg-stone-950 text-white hover:bg-stone-900"
          : "border-stone-200 bg-stone-50 text-stone-950 hover:bg-white",
      )}
    >
      <p className={cn("text-xs font-medium uppercase", dark ? "text-stone-400" : "text-stone-500")}>{label}</p>
      <p className="mt-3 line-clamp-2 text-lg font-semibold leading-6">{value}</p>
      <p className={cn("mt-2 line-clamp-3 text-sm leading-6", dark ? "text-stone-300" : "text-muted-foreground")}>{detail}</p>
      <p className={cn("mt-4 inline-flex items-center gap-2 text-sm font-medium", dark ? "text-white" : "text-stone-900")}>
        {action}
        <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
      </p>
    </Link>
  );
}

function MissionList({ title, items, empty, href }: { title: string; items: string[]; empty: string; href: string }) {
  return (
    <div className="min-h-48 rounded-lg border border-stone-200 bg-stone-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-medium uppercase text-stone-500">{title}</p>
        <Link href={href} className="text-xs font-medium text-stone-600 transition hover:text-stone-950">Open</Link>
      </div>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <p key={item} className="line-clamp-2 rounded-md bg-white px-3 py-2 text-sm leading-5 text-stone-800">
            {item}
          </p>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </div>
  );
}

function ContinuityCommandPanel({
  command,
  returningUser,
}: {
  command: ReturnType<typeof getContinuityCommand>;
  returningUser?: Dashboard["returning_user"];
}) {
  return (
    <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)_auto] lg:items-center">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
            <Target className="h-3.5 w-3.5" />
            Current focus
          </p>
          <h2 className="mt-2 line-clamp-2 text-xl font-semibold leading-7">{command.focusTitle}</h2>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-300">{command.focusDetail}</p>
        </div>
        <div className="min-w-0 rounded-lg border border-white/10 bg-white/5 p-4">
          <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
            <ArrowRight className="h-3.5 w-3.5" />
            Recommended next step
          </p>
          <p className="mt-2 line-clamp-2 text-base font-semibold">{command.nextTitle}</p>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-300">{command.nextDetail}</p>
        </div>
        <div className="flex flex-col gap-2 lg:w-44">
          <Link
            href={command.href}
            onClick={() => api.trackEvent("continuity_command_opened", "dashboard", { target: command.href, source: command.source })}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-stone-950 transition hover:bg-stone-100"
          >
            {command.actionLabel}
            <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="text-xs leading-5 text-stone-400">
            {returningUser?.is_returning ? returningUser.summary || "Context restored from your last session." : command.contextLine}
          </p>
        </div>
      </div>
    </section>
  );
}

function ContinuityAssistantPanel({ assistant }: { assistant: ContinuityAssistant | null }) {
  if (!assistant) return null;
  return (
    <SectionShell icon={<Sparkles className="h-4 w-4" />} title={assistant.greeting} description={assistant.summary}>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.7fr)]">
        <div className="grid gap-3 sm:grid-cols-3">
          <AssistantList title="What matters" items={assistant.priorities} empty="Add one active goal or priority." />
          <AssistantList title="Open loops" items={assistant.open_loops} empty="No unfinished work needs attention." />
          <AssistantList title="Recent progress" items={assistant.recent_progress} empty="Recent progress will appear here." />
        </div>
        <div className="rounded-lg bg-stone-950 p-4 text-white">
          <p className="text-xs font-medium uppercase text-stone-400">Recommended next step</p>
          <p className="mt-2 text-base font-semibold">{assistant.recommendation.title}</p>
          <p className="mt-2 text-sm leading-6 text-stone-300">{assistant.recommendation.detail}</p>
          <p className="mt-3 text-xs leading-5 text-stone-400">{assistant.recommendation.reason}</p>
        </div>
      </div>
    </SectionShell>
  );
}

function AssistantList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="rounded-lg bg-stone-50 p-4">
      <p className="text-xs font-medium uppercase text-stone-500">{title}</p>
      <ul className="mt-3 space-y-2">
        {items.slice(0, 4).map((item) => <li key={item} className="text-sm leading-5 text-stone-800">{item}</li>)}
        {!items.length && <li className="text-sm leading-5 text-stone-400">{empty}</li>}
      </ul>
    </div>
  );
}

function V2JourneyPanel({
  dashboard,
  workspace,
  assistant,
  dailyBrief,
  learning,
  continuityItems,
}: {
  dashboard: Dashboard | null;
  workspace: Workspace | null;
  assistant: ContinuityAssistant | null;
  dailyBrief: DailyBrief | null;
  learning: LearningEngine | null;
  continuityItems: ContinuityCard[];
}) {
  const firstProject = dashboard?.projects?.[0];
  const firstConversation = dashboard?.recent_conversations?.[0];
  const firstMemory = dashboard?.memories?.[0];
  const firstTimeline = dashboard?.continuity_timeline?.[0] || workspace?.timeline?.[0];
  const pendingSuggestion = learning?.suggestions.find((item) => item.status === "pending" || item.status === "edited");
  const approvedLearning = learning?.approved_understanding?.[0];
  const assistantRecommendation = assistant?.recommendation;

  const steps = [
    {
      id: "knows-you",
      icon: <UserRound className="h-4 w-4" />,
      label: "Knows you",
      title: firstMemory?.summary || firstMemory?.content || dailyBrief?.context.communication_style || "Add the context Synzept should carry.",
      detail: firstMemory ? firstMemory.category || firstMemory.memory_type : "Goals, preferences, role, and working style shape every next step.",
      href: "/knows-you",
      complete: Boolean(firstMemory || dailyBrief?.context.communication_style),
      action: "Review",
    },
    {
      id: "project",
      icon: <FolderKanban className="h-4 w-4" />,
      label: "Understands work",
      title: firstProject?.name || workspace?.projects?.[0]?.title || "Create the first project anchor.",
      detail: firstProject?.context_summary || firstProject?.description || "Projects connect tasks, notes, memory, and AI threads.",
      href: firstProject ? `/projects/${firstProject.id}` : "/projects",
      complete: Boolean(firstProject || workspace?.projects?.length),
      action: firstProject ? "Open" : "Create",
    },
    {
      id: "conversation",
      icon: <MessageSquare className="h-4 w-4" />,
      label: "Starts with context",
      title: firstConversation?.title || "Start the first AI conversation.",
      detail: firstConversation?.summary || "The first thread becomes a continuation point instead of a throwaway chat.",
      href: firstConversation ? `/chat?conversation=${firstConversation.id}` : "/chat",
      complete: Boolean(firstConversation),
      action: firstConversation ? "Continue" : "Start",
    },
    {
      id: "brief",
      icon: <CalendarDays className="h-4 w-4" />,
      label: "Briefs the day",
      title: dailyBrief?.next_step || dashboard?.daily?.rhythm_prompt || "Generate today's first brief.",
      detail: dailyBrief?.summary || dashboard?.briefing || "Daily Brief turns your profile and work into one clear next step.",
      href: "/daily-brief",
      complete: Boolean(dailyBrief || dashboard?.daily || dashboard?.briefing),
      action: "Open",
    },
    {
      id: "timeline",
      icon: <Clock3 className="h-4 w-4" />,
      label: "Remembers events",
      title: firstTimeline ? ("headline" in firstTimeline ? firstTimeline.headline : firstTimeline.title) : "Important activity will land on the timeline.",
      detail: firstTimeline ? ("summary" in firstTimeline ? firstTimeline.summary : firstTimeline.detail) : "Project, task, note, and conversation changes become returnable history.",
      href: "/timeline",
      complete: Boolean(firstTimeline),
      action: "View",
    },
    {
      id: "learning",
      icon: <BookOpenCheck className="h-4 w-4" />,
      label: "Learns with consent",
      title: pendingSuggestion?.title || approvedLearning?.title || "Analyze activity for the first suggestion.",
      detail: pendingSuggestion?.description || approvedLearning?.value || "Learning Engine proposes patterns for review before they become understanding.",
      href: "/learning-engine",
      complete: Boolean(pendingSuggestion || approvedLearning),
      action: pendingSuggestion ? "Review" : "Analyze",
    },
    {
      id: "continuity",
      icon: <Sparkles className="h-4 w-4" />,
      label: "Helps continue",
      title: assistantRecommendation?.title || continuityItems[0]?.title || "Synzept will recommend where to resume.",
      detail: assistantRecommendation?.detail || continuityItems[0]?.description || "Continuity Assistant uses the full path to keep the next session warm.",
      href: continuityItems[0]?.href || "/dashboard",
      complete: Boolean(assistantRecommendation || continuityItems.length),
      action: "Resume",
    },
  ];

  const completed = steps.filter((step) => step.complete).length;
  const lead = steps.find((step) => !step.complete) || steps[steps.length - 1];

  return (
    <SectionShell
      icon={<Sparkles className="h-4 w-4" />}
      title="First Session Journey"
      description="One connected path from profile context to the next useful recommendation."
      actionHref={lead.href}
      actionLabel={lead.action}
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-7">
          {steps.map((step, index) => (
            <Link
              key={step.id}
              href={step.href}
              onClick={() => api.trackEvent("v2_journey_step_opened", "dashboard", { step: step.id, complete: step.complete })}
              className={cn(
                "group min-h-40 rounded-lg border p-3 transition hover:bg-white",
                step.complete ? "border-stone-200 bg-white" : "border-dashed border-stone-300 bg-stone-50",
                "md:min-h-36 xl:min-h-48",
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <span className={cn("grid h-8 w-8 shrink-0 place-items-center rounded-md", step.complete ? "bg-stone-900 text-white" : "bg-white text-stone-500")}>
                  {step.complete ? <CheckCircle2 className="h-4 w-4" /> : step.icon}
                </span>
                <span className="text-xs font-medium text-stone-400">{index + 1}</span>
              </div>
              <p className="mt-3 text-xs font-medium uppercase text-stone-500">{step.label}</p>
              <p className="mt-2 line-clamp-2 text-sm font-semibold leading-5 text-stone-950">{step.title}</p>
              <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">{step.detail}</p>
            </Link>
          ))}
        </div>
        <div className="rounded-lg bg-stone-950 p-4 text-white">
          <p className="text-xs font-medium uppercase text-stone-400">Journey state</p>
          <p className="mt-2 text-3xl font-semibold">{completed}/{steps.length}</p>
          <p className="mt-2 text-sm leading-6 text-stone-300">
            {lead.complete
              ? "The core V2 loop is connected. Keep using projects and conversations to strengthen recommendations."
              : `${lead.label}: ${lead.title}`}
          </p>
          <Link
            href={lead.href}
            onClick={() => api.trackEvent("v2_journey_next_action_opened", "dashboard", { step: lead.id })}
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-white px-3 py-2 text-sm font-medium text-stone-950 transition hover:bg-stone-100"
          >
            {lead.action}
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </SectionShell>
  );
}

function ProactiveIntelligencePanel({ overview }: { overview: ProactiveOverview | null }) {
  if (!overview) return null;
  const action = overview.focus.highest_impact_action;

  return (
    <SectionShell icon={<Sparkles className="h-4 w-4" />} title="Proactive Intelligence" description="The clearest focus, project health signals, and next actions Synzept can see right now.">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
        <div className="space-y-3">
          <div className="rounded-lg bg-stone-950 p-4 text-white">
            <p className="text-xs font-medium uppercase text-stone-400">Highest leverage action</p>
            <p className="mt-2 text-base font-semibold">{action?.title || "Choose one meaningful next action"}</p>
            <p className="mt-2 text-sm leading-6 text-stone-300">{action?.detail || "Add a task or milestone and Synzept will turn it into a focused recommendation."}</p>
          </div>
          {!!overview.daily_plan.focus_areas.length && (
            <div className="space-y-2">
              {overview.daily_plan.focus_areas.map((area) => (
                <div key={area} className="rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-800">{area}</div>
              ))}
            </div>
          )}
          {overview.focus.attention_warning && <p className="rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">{overview.focus.attention_warning}</p>}
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <p className="mb-2 text-xs font-medium uppercase text-stone-500">Project health</p>
            <div className="space-y-2">
              {overview.project_health.slice(0, 3).map((project) => (
                <div key={project.project_id} className="rounded-md bg-stone-50 px-3 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-stone-900">{project.project_title}</p>
                    <Badge variant={project.risk_score >= 40 ? "accent" : "muted"}>{Math.round(project.health_score)}/100</Badge>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{project.reasons[0]}</p>
                </div>
              ))}
              {!overview.project_health.length && <EmptyLine text="Project health appears once you create a project." />}
            </div>
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase text-stone-500">Insight feed</p>
            <div className="space-y-2">
              {overview.insights.slice(0, 4).map((insight) => (
                <div key={`${insight.type}-${insight.title}`} className="rounded-md border border-stone-200 bg-white px-3 py-3">
                  <p className="text-sm font-medium text-stone-900">{insight.title}</p>
                  <p className="mt-1 text-xs leading-5 text-muted-foreground">{insight.detail}</p>
                </div>
              ))}
              {!overview.insights.length && <EmptyLine text="No attention signal is pulling focus right now." />}
            </div>
          </div>
        </div>
      </div>
    </SectionShell>
  );
}

function WorkspaceOverviewPanel({ workspace }: { workspace: Workspace | null }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<WorkspaceSearchResult[]>([]);

  const search = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim()) return setResults([]);
    setResults((await api.searchWorkspace(query.trim())).results);
  };

  if (!workspace) return null;

  return (
    <SectionShell icon={<Target className="h-4 w-4" />} title="Workspace Overview" description="Goals, progress, attention signals, and the clearest work to move today.">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.75fr)]">
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            <ProgressMetric label="Goals" value={workspace.progress.goal_completion} />
            <ProgressMetric label="Projects" value={workspace.progress.project_completion} />
            <ProgressMetric label="Tasks" value={workspace.progress.task_completion} />
          </div>
          {workspace.goals.filter((goal) => goal.status === "active").slice(0, 4).map((goal) => (
            <div key={goal.id} className="rounded-lg border border-stone-200 bg-white p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-stone-950">{goal.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{goal.milestones.length} milestone{goal.milestones.length === 1 ? "" : "s"}</p>
                </div>
                <p className="text-sm font-semibold text-stone-800">{Math.round(goal.progress)}%</p>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-stone-100">
                <div className="h-full rounded-full bg-stone-800" style={{ width: `${goal.progress}%` }} />
              </div>
            </div>
          ))}
          {workspace.insights.slice(0, 3).map((insight) => (
            <div key={`${insight.type}-${insight.title}`} className="rounded-md border border-amber-100 bg-amber-50 px-3 py-2">
              <p className="text-sm font-medium text-stone-900">{insight.title}</p>
              <p className="mt-1 text-xs leading-5 text-stone-600">{insight.detail}</p>
            </div>
          ))}
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase text-stone-500">Recommended today</p>
          <div className="space-y-2">
            {workspace.recommendations.slice(0, 4).map((action) => (
              <Link key={`${action.goal_id}-${action.milestone_id}-${action.task_id}-${action.title}`} href="/tasks" className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium text-stone-900">{action.title}</p>
                    <p className="mt-1 text-xs leading-5 text-muted-foreground">{action.goal_title}{action.milestone_title ? ` - ${action.milestone_title}` : ""}</p>
                  </div>
                  <Badge variant={action.priority === "high" ? "accent" : "muted"}>{action.priority}</Badge>
                </div>
              </Link>
            ))}
          </div>
          <form onSubmit={search} className="mt-4">
            <p className="mb-2 text-xs font-medium uppercase text-stone-500">Search workspace</p>
            <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search projects, goals, tasks, notes, memories" />
            {!!results.length && (
              <div className="mt-2 space-y-1">
                {results.slice(0, 5).map((item) => (
                  <div key={`${item.type}-${item.id}`} className="rounded-md bg-stone-50 px-3 py-2">
                    <p className="text-xs uppercase text-stone-500">{item.type}</p>
                    <p className="text-sm text-stone-900">{item.title}</p>
                  </div>
                ))}
              </div>
            )}
          </form>
        </div>
      </div>
    </SectionShell>
  );
}

function ProgressMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-3">
      <p className="text-lg font-semibold text-stone-950">{Math.round(value)}%</p>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
    </div>
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

function ContinuitySection({ items, returningUser }: { items: ContinuityCard[]; returningUser?: Dashboard["returning_user"] }) {
  const lead = items[0];
  const supporting = items.slice(1, 5);
  const returnLine = returningUser?.summary || returningUser?.prompt;

  return (
    <SectionShell
      icon={<Clock3 className="h-4 w-4" />}
      title="Continue where you left off"
      description={returnLine || "The fastest path back into recent projects, active conversations, remembered context, and open loops."}
      actionHref={lead?.href}
      actionLabel={lead ? "Resume" : undefined}
    >
      {returningUser?.is_returning && (
        <div className="mb-3 rounded-lg border border-accent/20 bg-accent-muted/10 p-4">
          <p className="text-xs font-medium uppercase text-accent-foreground">Welcome back</p>
          <p className="mt-2 text-sm leading-6 text-stone-800">
            {returningUser.prompt ||
              `You were here ${returningUser.days_since_last_seen ?? "recently"}. Synzept kept your recent context ready.`}
          </p>
          {!!returningUser.signals?.length && (
            <div className="mt-3 flex flex-wrap gap-2">
              {returningUser.signals.slice(0, 3).map((signal) => (
                <Link
                  key={`${signal.type}-${signal.label}`}
                  href={signal.href || "/dashboard"}
                  className="rounded-md border border-accent/20 bg-white px-2.5 py-1.5 text-xs text-stone-700 transition hover:bg-stone-50"
                >
                  {signal.label}
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
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
            <p className="mt-5 text-sm font-medium text-stone-900">{lead.action_label || "Continue now"}</p>
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
            <Link href="/projects" onClick={() => api.trackEvent("restore_point_intent", "dashboard", { target: "project" })} className="rounded-md border border-stone-200 bg-stone-50 px-3 py-3 text-sm text-stone-700 transition hover:bg-white">Create a project</Link>
            <Link href="/tasks" onClick={() => api.trackEvent("restore_point_intent", "dashboard", { target: "task" })} className="rounded-md border border-stone-200 bg-stone-50 px-3 py-3 text-sm text-stone-700 transition hover:bg-white">Add one next action</Link>
            <Link href="/chat" onClick={() => api.trackEvent("restore_point_intent", "dashboard", { target: "chat" })} className="rounded-md border border-stone-200 bg-stone-50 px-3 py-3 text-sm text-stone-700 transition hover:bg-white">Start a thread</Link>
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
  dailyBrief,
  learning,
  assistant,
  priorities,
  continuationItems,
  onSaved,
  onLearningAnalyzed,
}: {
  daily: DailyExperience | null;
  dailyBrief: DailyBrief | null;
  learning: LearningEngine | null;
  assistant: ContinuityAssistant | null;
  priorities: Task[];
  continuationItems: ContinuityCard[];
  onSaved: () => Promise<unknown> | unknown;
  onLearningAnalyzed: (engine: LearningEngine) => void;
}) {
  const [progress, setProgress] = useState("");
  const [completed, setCompleted] = useState("");
  const [unfinished, setUnfinished] = useState("");
  const [insights, setInsights] = useState("");
  const [tomorrow, setTomorrow] = useState("");
  const [resume, setResume] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const phase = daily?.workflow_phase || "morning";
  const morningFocus = daily?.focus_areas?.[0] || dailyBrief?.context.what_matters?.[0] || priorities[0]?.title || "Choose one meaningful focus.";
  const morningRecommendation = dailyBrief?.next_step || daily?.suggestions?.[0]?.description || daily?.suggestions?.[0]?.label || continuationItems[0]?.action_label || "Start with the clearest unfinished thread.";
  const morningPriority = priorities[0]?.title || dailyBrief?.context.what_matters?.[0] || continuationItems[0]?.title || "Create one priority for today.";
  const unfinishedItems = dailyBrief?.open_loops?.length ? dailyBrief.open_loops : priorities.slice(0, 3).map((task) => task.title);
  const meaningfulEvents = [
    ...(dailyBrief?.context.recent_progress || []).map((item) => item.title),
    ...(daily?.completed_today || []),
    ...continuationItems.map((item) => item.title),
  ].filter(Boolean);
  const pendingSuggestions = learning?.suggestions.filter((item) => item.status === "pending" || item.status === "edited") || [];
  const tomorrowStarts = [
    ...(daily?.tomorrow_priorities || []),
    ...(daily?.continuation_points || []),
    assistant?.recommendation.title,
    continuationItems[0]?.continuation_prompt || continuationItems[0]?.title,
  ].filter(Boolean) as string[];

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setSaveMessage(null);
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
      const analyzed = await learningEngineApi.analyze().catch(() => null);
      if (analyzed) onLearningAnalyzed(analyzed);
      await onSaved();
      setSaveMessage("Wrap-up saved. Tomorrow's starting point is prepared; learning suggestions are waiting for approval.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionShell
      icon={<CalendarDays className="h-4 w-4" />}
      title="Daily Operating Loop"
      description="Morning clarity, quiet work, and a closing loop that prepares tomorrow."
    >
      <div className="grid gap-4 xl:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <div className="space-y-3">
          <div className="rounded-lg border border-stone-200 bg-stone-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <Badge variant={phase === "closed" ? "accent" : "muted"}>{phase.replace("_", " ")}</Badge>
              <Link href="/daily-brief" className="text-xs font-medium text-stone-600 transition hover:text-stone-950">Open brief</Link>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <LoopSignal label="One focus" value={morningFocus} />
              <LoopSignal label="One recommendation" value={morningRecommendation} />
              <LoopSignal label="One priority" value={morningPriority} />
            </div>
            <p className="mt-4 text-sm leading-6 text-stone-700">
              {daily?.rhythm_prompt || "Start with one focus. Everything else can remain context until it needs action."}
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <RhythmList
              title="Unfinished"
              items={unfinishedItems.slice(0, 3)}
              empty="No open loop needs attention right now."
            />
            <RhythmList
              title="Tomorrow prepared"
              items={tomorrowStarts.slice(0, 3)}
              empty="Wrap up once to preload the next session."
            />
          </div>

          <div className="rounded-lg border border-stone-200 bg-white p-4">
            <p className="text-xs font-medium uppercase text-stone-500">Quiet work surfaces</p>
            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
              <WorkSurface href="/projects" label="Projects" detail="Work context" />
              <WorkSurface href="/chat" label="AI" detail="Thinking thread" />
              <WorkSurface href="/notes" label="Notes" detail="Raw material" />
              <WorkSurface href="/memory" label="Memory" detail="Saved context" />
            </div>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">Synzept observes these surfaces in the background. No notifications, nudges, or interruptions.</p>
          </div>

          <RhythmList
            title="Meaningful timeline updates"
            items={uniqueItems(meaningfulEvents).slice(0, 4)}
            empty="Only meaningful progress is saved. Routine clicks and small edits stay out of the timeline."
          />

          <RhythmList
            title="Return points"
            items={continuationItems.map((item) => item.continuation_prompt || item.title).slice(0, 3)}
            empty="Continuation cards will become your midday restore points."
          />
        </div>

        <form onSubmit={save} className="space-y-3 rounded-lg border border-stone-200 bg-white p-4">
          <div>
            <p className="text-sm font-semibold text-stone-950">Continuity Wrap-Up</p>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Close the session by saving only what helps tomorrow begin cleanly.
            </p>
          </div>
          <Textarea value={progress} onChange={(event) => setProgress(event.target.value)} placeholder="What changed today?" rows={3} />
          <div className="grid gap-3 md:grid-cols-2">
            <Textarea value={completed} onChange={(event) => setCompleted(event.target.value)} placeholder="Completed, one per line" rows={3} />
            <Textarea value={unfinished} onChange={(event) => setUnfinished(event.target.value)} placeholder="Still open, one per line" rows={3} />
            <Textarea value={tomorrow} onChange={(event) => setTomorrow(event.target.value)} placeholder="What should tomorrow begin with?" rows={3} />
            <Textarea value={resume} onChange={(event) => setResume(event.target.value)} placeholder="Continuation points, one per line" rows={3} />
          </div>
          <Textarea value={insights} onChange={(event) => setInsights(event.target.value)} placeholder="Context worth remembering or learning from" rows={2} />
          <div className="rounded-lg bg-stone-50 p-3">
            <p className="text-xs font-medium uppercase text-stone-500">Learning review</p>
            <p className="mt-2 text-sm leading-6 text-stone-700">
              {pendingSuggestions.length
                ? `${pendingSuggestions.length} suggestion${pendingSuggestions.length === 1 ? "" : "s"} waiting. Nothing becomes understanding until you approve it.`
                : "After wrap-up, Synzept analyzes the session and prepares suggestions for approval."}
            </p>
            {pendingSuggestions.length > 0 && (
              <Link href="/learning-engine" className="mt-2 inline-block text-xs font-medium text-stone-700 transition hover:text-stone-950">
                Review suggestions
              </Link>
            )}
          </div>
          {saveMessage && <p className="rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{saveMessage}</p>}
          <div className="flex flex-wrap items-center gap-2">
            <Button type="submit" size="sm" disabled={saving || !hasWrapUpInput(progress, completed, unfinished, insights, tomorrow, resume)}>
              <Save className="mr-1.5 h-4 w-4" />
              {saving ? "Saving..." : "Save wrap-up"}
            </Button>
            <Link href="/timeline" className="rounded-md px-2 py-1 text-xs font-medium text-stone-600 transition hover:bg-stone-100 hover:text-stone-950">
              View timeline
            </Link>
          </div>
        </form>
      </div>
    </SectionShell>
  );
}

function LoopSignal({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white px-3 py-3">
      <p className="text-xs font-medium uppercase text-stone-500">{label}</p>
      <p className="mt-2 line-clamp-3 text-sm font-medium leading-5 text-stone-900">{value}</p>
    </div>
  );
}

function WorkSurface({ href, label, detail }: { href: string; label: string; detail: string }) {
  return (
    <Link href={href} className="rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
      <p className="text-sm font-medium text-stone-900">{label}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </Link>
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

function getRecentChanges(
  dashboard: Dashboard | null,
  assistant: ContinuityAssistant | null,
  dailyBrief: DailyBrief | null,
  continuityItems: ContinuityCard[],
) {
  return uniqueItems([
    ...(assistant?.recent_progress || []),
    ...(dailyBrief?.context.recent_progress || []).map((item) => item.title),
    ...(dashboard?.daily?.completed_today || []),
    ...(dashboard?.recent_activity || []).map((item) => item.title),
    ...(dashboard?.continuity_timeline || []).map((item) => item.headline),
    ...continuityItems
      .filter((item) => item.reason || item.updated_at)
      .map((item) => item.reason || `${item.title} was updated.`),
  ]);
}

function getContinuityCommand({
  dashboard,
  workspace,
  assistant,
  dailyBrief,
  priorityTasks,
  continuityItems,
  focusAreas,
}: {
  dashboard: Dashboard | null;
  workspace: Workspace | null;
  assistant: ContinuityAssistant | null;
  dailyBrief: DailyBrief | null;
  priorityTasks: Task[];
  continuityItems: ContinuityCard[];
  focusAreas: string[];
}) {
  const leadProject = dashboard?.projects?.find((project) => project.currentFocus || project.recommendedNextStep) || dashboard?.projects?.[0];
  const workspaceProject = workspace?.projects?.[0];
  const leadTask = priorityTasks[0];
  const leadContinuation = continuityItems[0];
  const focusTitle =
    focusAreas[0] ||
    leadProject?.currentFocus ||
    dailyBrief?.context.what_matters?.[0] ||
    leadTask?.title ||
    leadContinuation?.title ||
    workspaceProject?.title ||
    "Choose one thing to continue.";
  const focusDetail =
    leadProject?.name ||
    workspaceProject?.description ||
    dailyBrief?.summary ||
    dashboard?.continuity_summary ||
    leadContinuation?.description ||
    "Synzept becomes more useful once one project, task, note, or thread becomes the visible anchor.";
  const nextTitle =
    assistant?.recommendation.title ||
    leadProject?.recommendedNextStep ||
    dailyBrief?.next_step ||
    leadTask?.title ||
    leadContinuation?.action_label ||
    "Create a restore point.";
  const nextDetail =
    assistant?.recommendation.detail ||
    leadContinuation?.continuation_prompt ||
    leadContinuation?.description ||
    "Add one next action or open a recent thread so the next session starts from momentum.";
  const href =
    leadContinuation?.href ||
    (leadProject?.id ? `/projects/${leadProject.id}` : "") ||
    (leadTask ? "/tasks" : "") ||
    "/projects";

  return {
    focusTitle,
    focusDetail,
    nextTitle,
    nextDetail,
    href,
    actionLabel: leadContinuation?.action_label || (leadTask ? "Open task" : leadProject ? "Open project" : "Start setup"),
    source: leadContinuation?.type || (leadTask ? "task" : leadProject ? "project" : "empty"),
    contextLine: "This is the fastest path back into useful work.",
  };
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

function uniqueItems(values: string[]) {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
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

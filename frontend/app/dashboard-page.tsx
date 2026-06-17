"use client";

import { useCallback, useEffect, useMemo, useState, useTransition, type ReactNode } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, CheckCircle2, CircleDot, ClipboardCheck, FolderKanban, MessageSquare, RotateCcw, Sparkles, Target, TriangleAlert, type LucideIcon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { UpgradeCta } from "@/components/pro/upgrade-cta";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type AutonomousWorkspace, type ChiefOfStaff, type ContinuityAssistant, type ContinuityCard, type Conversation, type DailyBriefSnapshot, type Dashboard, type IntelligenceItem, type PersonalOS, type Project, type ReturningUser, type Task } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/auth";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";

const doneStatuses = new Set(["completed", "archived", "done"]);
const priorityRank: Record<string, number> = { high: 3, medium: 2, low: 1 };

export function DashboardPage() {
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const isPro = Boolean(useAuthStore((state) => state.user?.is_pro));
  const [, startTransition] = useTransition();
  const [assistant, setAssistant] = useState<ContinuityAssistant | null>(null);
  const [dailyBrief, setDailyBrief] = useState<DailyBriefSnapshot | null>(null);
  const [chiefOfStaff, setChiefOfStaff] = useState<ChiefOfStaff | null>(null);
  const [autonomousWorkspace, setAutonomousWorkspace] = useState<AutonomousWorkspace | null>(null);
  const [workspaceRefreshing, setWorkspaceRefreshing] = useState(false);
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
    api.getDailyBriefV2().then(setDailyBrief).catch(() => setDailyBrief(null));
  }, []);

  useEffect(() => {
    api.getChiefOfStaff().then(setChiefOfStaff).catch(() => setChiefOfStaff(null));
  }, []);

  const loadAutonomousWorkspace = useCallback(() => {
    return api.getAutonomousWorkspace().then(setAutonomousWorkspace).catch(() => setAutonomousWorkspace(null));
  }, []);

  useEffect(() => {
    loadAutonomousWorkspace();
  }, [loadAutonomousWorkspace]);

  const refreshAutonomousSuggestions = useCallback(() => {
    setWorkspaceRefreshing(true);
    api
      .generateAutonomousSuggestions()
      .then((suggestions) => {
        setAutonomousWorkspace((current) => current ? { ...current, suggestions } : current);
        void api.trackEvent("autonomous_suggestions_refreshed", "dashboard", { count: suggestions.length });
      })
      .then(loadAutonomousWorkspace)
      .catch(() => null)
      .finally(() => setWorkspaceRefreshing(false));
  }, [loadAutonomousWorkspace]);

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
  const personalOS = dashboard?.personal_os || null;
  const openLoops = useMemo(() => getOpenLoops({ dashboard, assistant, priorityTasks, continuityItems, personalOS }), [assistant, continuityItems, dashboard, personalOS, priorityTasks]);
  const recentProgress = useMemo(() => getRecentProgress({ dashboard, assistant, continuityItems, personalOS }), [assistant, continuityItems, dashboard, personalOS]);

  const whatMatters = useMemo(() => getWhatMattersToday(dashboard, assistant, focusAreas, personalOS), [assistant, dashboard, focusAreas, personalOS]);
  const returnStats = useMemo(() => getReturnStats(dashboard, openLoops, recentProgress), [dashboard, openLoops, recentProgress]);

  return (
    <PageFrame eyebrow="Personal intelligence" title="Personal OS">
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {isLoading && !dashboard ? (
          <DashboardSkeleton />
        ) : (
          <>
            {dashboard?.returning_user?.is_returning && (
              <ReturnToWorkPanel returningUser={dashboard.returning_user} fallbackStats={returnStats} />
            )}
            {!isPro && <DashboardUpgradePanel />}
            <PersonalOSHero os={personalOS} command={command} />
            <ChiefOfStaffPanel chief={chiefOfStaff} fallbackNext={command.nextTitle} />
            <AutonomousWorkspacePanel workspace={autonomousWorkspace} refreshing={workspaceRefreshing} onRefresh={refreshAutonomousSuggestions} fallbackNext={command.nextTitle} />
            <DailyBriefPreview brief={dailyBrief} fallbackNext={command.nextTitle} />
            <section className="grid gap-5 lg:grid-cols-[minmax(0,1.2fr)_minmax(300px,0.8fr)]">
              <CompactList title="What Matters Today" items={whatMatters} empty="Create a project focus or task to give Synzept a daily brief." />
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
            <ContinuityPanel items={continuityItems} />
          </>
        )}
      </div>
    </PageFrame>
  );
}

function DashboardUpgradePanel() {
  return (
    <section className="rounded-lg border border-amber-200 bg-amber-50 p-5 shadow-soft">
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
        <div>
          <p className="text-sm font-semibold text-stone-950">Synzept Pro - ₹399/month</p>
          <p className="mt-1 text-sm leading-6 text-stone-700">
            Unlock Advanced Daily Brief, Open Loops, Project Intelligence, Continuity Assistant, and priority AI features.
          </p>
        </div>
        <UpgradeCta />
      </div>
    </section>
  );
}

function PersonalOSHero({ os, command }: { os: PersonalOS | null; command: ReturnType<typeof getContinuityCommand> }) {
  const mission = os?.current_mission || "Build one clear anchor for your work today.";
  const focus = os?.current_focus || command.focusTitle;
  const next = os?.suggested_next_action || { title: command.nextTitle, reason: command.nextDetail, href: command.href };
  const stats = [
    { label: "Priorities", value: os?.top_priorities?.length || 1 },
    { label: "Open Loops", value: os?.open_loops?.length || 0 },
    { label: "Projects", value: os?.active_projects?.length || 0 },
    { label: "Decisions", value: os?.recent_decisions?.length || 0 },
  ];

  return (
    <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft md:p-6">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(300px,0.58fr)] lg:items-start">
        <div className="min-w-0">
          <p className="text-sm font-medium text-stone-300">{os?.greeting || "Good morning, there"}</p>
          <h1 className="mt-3 text-3xl font-semibold leading-9 md:text-4xl md:leading-[2.8rem]">Current Mission</h1>
          <p className="mt-3 max-w-3xl text-xl leading-8 text-white">{mission}</p>
          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <OSDetail label="Current Focus" value={focus} />
            <OSDetail label="Suggested Next Action" value={next.title} href={next.href} />
          </div>
        </div>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {stats.map((stat) => (
              <div key={stat.label} className="rounded-md border border-white/10 bg-white/5 px-3 py-3">
                <p className="text-2xl font-semibold">{stat.value}</p>
                <p className="mt-1 text-xs text-stone-400">{stat.label}</p>
              </div>
            ))}
          </div>
          <Link href={next.href || command.href} className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-white px-4 text-sm font-medium text-stone-950 transition hover:bg-stone-100">
            Continue
            <ArrowRight className="h-4 w-4" />
          </Link>
          <p className="text-xs leading-5 text-stone-400">{next.reason || command.nextDetail}</p>
        </div>
      </div>
    </section>
  );
}

function OSDetail({ label, value, href }: { label: string; value: string; href?: string }) {
  const content = (
    <>
      <p className="text-xs font-medium uppercase text-stone-400">{label}</p>
      <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-100">{value}</p>
    </>
  );
  if (href) {
    return (
      <Link href={href} className="rounded-lg border border-white/10 bg-white/5 p-4 transition hover:bg-white/10">
        {content}
      </Link>
    );
  }
  return <div className="rounded-lg border border-white/10 bg-white/5 p-4">{content}</div>;
}

function ChiefOfStaffPanel({ chief, fallbackNext }: { chief: ChiefOfStaff | null; fallbackNext: string }) {
  const next = chief?.executive_brief.recommended_next_action;
  const momentum = chief?.momentum;
  const risks = chief?.risks || [];
  const opportunities = chief?.opportunities || [];
  const suggestions = chief?.strategic_suggestions || [];

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div>
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted">
            <Sparkles className="h-3.5 w-3.5" />
            AI Chief of Staff
          </p>
          <h2 className="mt-2 text-xl font-semibold text-stone-950">Executive Brief</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <ChiefList title="What changed" items={chief?.executive_brief.what_changed || ["No major workspace changes were recorded in the last 3 days."]} />
            <ChiefList title="What matters now" items={chief?.executive_brief.what_matters_now || [fallbackNext]} />
          </div>
        </div>
        <div className="rounded-lg border border-stone-900 bg-stone-950 p-4 text-white">
          <p className="text-xs font-medium uppercase text-stone-400">Momentum</p>
          <div className="mt-2 flex items-end justify-between gap-3">
            <p className="text-4xl font-semibold">{Math.round(momentum?.score ?? 0)}</p>
            <Badge variant="muted">{momentum?.trend || "flat"}</Badge>
          </div>
          <p className="mt-3 text-xs leading-5 text-stone-300">{momentum?.explanation || "Momentum appears once Synzept sees activity and completion signals."}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <SignalColumn title="Needs Attention" icon={TriangleAlert} items={risks} empty="No major risk signals detected." tone="risk" />
        <SignalColumn title="Opportunities" icon={Sparkles} items={opportunities} empty="Opportunities appear as goals, projects, and activity connect." tone="opportunity" />
        <SignalColumn title="Strategic Suggestions" icon={Target} items={suggestions} empty={next?.title || fallbackNext} tone="strategy" />
      </div>
    </section>
  );
}

function ChiefList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md bg-stone-50 p-3">
      <p className="text-sm font-semibold text-stone-950">{title}</p>
      <div className="mt-2 space-y-1.5">
        {items.slice(0, 4).map((item) => (
          <p key={item} className="text-xs leading-5 text-stone-700">{item}</p>
        ))}
      </div>
    </div>
  );
}

function AutonomousWorkspacePanel({
  workspace,
  refreshing,
  onRefresh,
  fallbackNext,
}: {
  workspace: AutonomousWorkspace | null;
  refreshing: boolean;
  onRefresh: () => void;
  fallbackNext: string;
}) {
  const weekly = workspace?.weekly_plan;
  const execution = workspace?.execution;
  const suggestions = workspace?.suggestions || [];
  const health = workspace?.project_health || [];
  const counts = [
    { label: "Planned", value: execution?.planned.length ?? 0 },
    { label: "Completed", value: execution?.completed.length ?? 0 },
    { label: "Blocked", value: execution?.blocked.length ?? 0 },
  ];
  const thisWeek = weekly?.this_week?.length ? weekly.this_week : [{ title: fallbackNext, detail: "Primary next action from your current workspace context.", priority: "high", type: "fallback" } as IntelligenceItem];

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">
                <Target className="h-3.5 w-3.5" />
                Autonomous Workspace
              </p>
              <h2 className="mt-2 text-xl font-semibold text-stone-950">Execution plan for the week.</h2>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">{weekly?.priority_focus || fallbackNext}</p>
            </div>
            <button
              type="button"
              onClick={onRefresh}
              disabled={refreshing}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-md border border-border px-3 text-sm font-medium text-stone-700 transition hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Sparkles className="h-4 w-4" />
              {refreshing ? "Refreshing" : "Refresh"}
            </button>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <ExecutionList title="This Week" items={thisWeek} />
            <ExecutionList title="Next Week" items={weekly?.next_week || []} empty="Next week appears after Synzept has more planned work." />
          </div>
        </div>

        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            {counts.map((item) => (
              <div key={item.label} className="rounded-md bg-stone-50 px-3 py-3">
                <p className="text-2xl font-semibold text-stone-950">{item.value}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">{item.label}</p>
              </div>
            ))}
          </div>
          <div className="rounded-lg border border-stone-200 p-3">
            <p className="text-sm font-semibold text-stone-950">Project Health</p>
            <div className="mt-2 space-y-2">
              {health.slice(0, 3).map((project) => (
                <Link key={project.project_id} href={`/projects/${project.project_id}`} className="block rounded-md bg-stone-50 px-3 py-2 transition hover:bg-stone-100">
                  <div className="flex items-center justify-between gap-3">
                    <p className="line-clamp-1 text-xs font-medium text-stone-900">{project.project_title}</p>
                    <span className="text-xs text-stone-500">{Math.round(project.health_score)}%</span>
                  </div>
                </Link>
              ))}
              {!health.length && <p className="text-xs leading-5 text-muted-foreground">Project health appears once active projects have tasks, progress, or risks.</p>}
            </div>
          </div>
          <div className="rounded-lg border border-stone-200 p-3">
            <p className="text-sm font-semibold text-stone-950">Autonomous Suggestions</p>
            <div className="mt-2 space-y-2">
              {suggestions.slice(0, 3).map((item) => (
                <p key={item.id} className="rounded-md bg-stone-50 px-3 py-2 text-xs leading-5 text-stone-700">{item.title}</p>
              ))}
              {!suggestions.length && <p className="text-xs leading-5 text-muted-foreground">Synzept will suggest actions as goals, projects, and activity connect.</p>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function ExecutionList({ title, items, empty }: { title: string; items: IntelligenceItem[]; empty?: string }) {
  return (
    <div className="rounded-lg border border-stone-200 p-4">
      <p className="text-sm font-semibold text-stone-950">{title}</p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 4).map((item) => (
          <Link key={`${item.type}-${item.title}`} href={item.project_id ? `/projects/${item.project_id}` : "/tasks"} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <p className="line-clamp-2 text-sm font-medium text-stone-950">{item.title}</p>
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </Link>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">{empty || "No planned items yet."}</p>}
      </div>
    </div>
  );
}

function SignalColumn({
  title,
  icon: Icon,
  items,
  empty,
  tone,
}: {
  title: string;
  icon: LucideIcon;
  items: IntelligenceItem[];
  empty: string;
  tone: "risk" | "opportunity" | "strategy";
}) {
  const toneClass = tone === "risk" ? "border-amber-200 bg-amber-50" : tone === "opportunity" ? "border-emerald-200 bg-emerald-50" : "border-stone-200 bg-stone-50";
  return (
    <div className={`rounded-lg border p-4 ${toneClass}`}>
      <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
        <Icon className="h-4 w-4 text-stone-600" />
        {title}
      </p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 4).map((item) => (
          <Link key={`${item.type}-${item.title}`} href={item.project_id ? `/projects/${item.project_id}` : item.goal_id ? "/tasks" : "/dashboard"} className="block rounded-md bg-white/75 px-3 py-3 transition hover:bg-white">
            <p className="line-clamp-2 text-sm font-medium text-stone-950">{item.title}</p>
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </Link>
        ))}
        {!items.length && <p className="rounded-md bg-white/70 px-3 py-3 text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </div>
  );
}

function ReturnToWorkPanel({ returningUser, fallbackStats }: { returningUser: ReturningUser; fallbackStats: ReturnType<typeof getReturnStats> }) {
  const counts = returningUser.activity_counts;
  const stats = [
    { label: "Projects Updated", value: counts?.projects_updated ?? fallbackStats.updates, icon: FolderKanban },
    { label: "Tasks Completed", value: counts?.tasks_completed ?? fallbackStats.completed, icon: CheckCircle2 },
    { label: "Open Loops Created", value: counts?.open_loops_created ?? fallbackStats.openLoops, icon: RotateCcw },
    { label: "Decisions Made", value: counts?.decisions_made ?? 0, icon: ClipboardCheck },
    { label: "Milestones Reached", value: counts?.milestones_reached ?? 0, icon: Sparkles },
  ];
  const changed = returningUser.what_changed || [];
  const loops = returningUser.open_loops || [];
  const context = returningUser.context_to_remember || [];
  const recommendation = returningUser.recommended_next_step;
  const absence = returningUser.days_since_last_seen && returningUser.days_since_last_seen > 0
    ? `${returningUser.days_since_last_seen} day${returningUser.days_since_last_seen === 1 ? "" : "s"} away`
    : "Since your last visit";

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-5 shadow-soft">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start">
        <div>
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">
            <RotateCcw className="h-3.5 w-3.5" />
            {absence}
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-stone-950">Welcome Back</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
            {returningUser.summary || returningUser.prompt || "Synzept kept track of what changed, what is unfinished, and where to resume."}
          </p>
        </div>
        {recommendation && (
          <Link href={recommendation.href} className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-stone-900 px-4 text-sm font-medium text-white transition hover:bg-stone-800">
            Resume Work
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
        {stats.map((item) => (
          <ReturnStat key={item.label} label={item.label} value={item.value} icon={item.icon} />
        ))}
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(300px,0.9fr)]">
        <ReturnSection title="What Changed" empty="No project updates were recorded while you were away.">
          {changed.slice(0, 5).map((item) => (
            <Link key={`${item.type}-${item.id}`} href={item.href || "/dashboard"} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="line-clamp-1 text-sm font-medium text-stone-950">{item.project_name}</p>
                  <p className="mt-1 line-clamp-1 text-sm text-stone-800">{item.title}</p>
                  {item.description && <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.description}</p>}
                </div>
                <span className="shrink-0 rounded-md bg-white px-2 py-1 text-[11px] text-stone-500">{labelForType(item.type)}</span>
              </div>
            </Link>
          ))}
        </ReturnSection>

        <div className="space-y-4">
          <ReturnSection title="Open Loops" empty="No outstanding loop needs attention right now.">
            {loops.slice(0, 4).map((item) => (
              <Link key={item.id} href={item.href || "/open-loops"} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="line-clamp-1 text-sm font-medium text-stone-950">{item.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.project_name} - {item.next_step || item.description}</p>
                  </div>
                  <Badge variant={item.priority === "high" ? "accent" : "muted"}>{item.priority}</Badge>
                </div>
              </Link>
            ))}
          </ReturnSection>

          {recommendation && (
            <div className="rounded-lg border border-stone-900 bg-stone-950 p-4 text-white">
              <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
                <Target className="h-3.5 w-3.5" />
                Recommended Next Step
              </p>
              <p className="mt-2 line-clamp-2 text-base font-semibold">{recommendation.title}</p>
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-300">{recommendation.reason}</p>
            </div>
          )}
        </div>
      </div>

      <ReturnSection title="Context To Remember" empty="No critical reminders were found.">
        {context.length ? (
          <div className="grid gap-2 md:grid-cols-2">
            {context.slice(0, 4).map((item) => (
              <Link key={`${item.type}-${item.title}`} href={item.href || "/dashboard"} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
                <p className="line-clamp-1 text-sm font-medium text-stone-950">{item.title}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
              </Link>
            ))}
          </div>
        ) : null}
      </ReturnSection>
    </section>
  );
}

function ReturnStat({ label, value, icon: Icon }: { label: string; value: number; icon: LucideIcon }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-2xl font-semibold text-stone-950">{value}</p>
        <Icon className="h-4 w-4 text-stone-400" />
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

function ReturnSection({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const hasChildren = Array.isArray(children) ? children.some(Boolean) : Boolean(children);
  return (
    <div className="rounded-lg border border-stone-200 p-4">
      <p className="text-sm font-semibold text-stone-950">{title}</p>
      <div className="mt-3 space-y-2">
        {hasChildren ? children : <p className="text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </div>
  );
}

function DailyBriefPreview({ brief, fallbackNext }: { brief: DailyBriefSnapshot | null; fallbackNext: string }) {
  const nextStep = briefItem(brief?.recommendedNextStep, fallbackNext || "Set one concrete outcome for today.");
  const matters = brief?.whatMattersToday.length ?? 0;
  const loops = brief?.openLoops.length ?? 0;
  const projects = brief?.projectsNeedingAttention.length ?? 0;

  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">
            <CalendarDays className="h-3.5 w-3.5" />
            Daily Brief
          </p>
          <h2 className="mt-2 text-xl font-semibold text-stone-950">Know what to focus on right now.</h2>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-muted-foreground">
            {nextStep.title}
            {nextStep.detail ? ` — ${nextStep.detail}` : ""}
          </p>
          <div className="mt-4 grid max-w-md grid-cols-3 gap-2">
            <BriefMetric label="Priorities" value={matters} />
            <BriefMetric label="Open loops" value={loops} />
            <BriefMetric label="Projects" value={projects} />
          </div>
        </div>
        <Link href="/daily-brief" className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-stone-900 px-4 text-sm font-medium text-white transition hover:bg-stone-800">
          Open Daily Brief
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </section>
  );
}

function BriefMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-2">
      <p className="text-lg font-semibold text-stone-950">{value}</p>
      <p className="mt-1 text-[11px] text-muted-foreground">{label}</p>
    </div>
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
      <SectionHeading title={title} description={title === "What Matters Today" ? "Top priorities, important projects, and time-sensitive items." : undefined} />
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
      <SectionHeading title="Current Projects" description="Active projects only, with visible status and last movement." />
      <div className="mt-3 space-y-2">
        {active.map((project) => (
          <Link key={project.id} href={`/projects/${project.id}`} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="line-clamp-1 text-sm font-medium text-stone-950">{project.name}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                  {project.currentFocus || project.recommendedNextStep || project.description || "Add a focus and next step."}
                </p>
                <p className="mt-1 text-xs text-stone-400">{project.updatedAt || project.createdAt || project.created_at ? `Last activity ${formatShortDate(project.updatedAt || project.createdAt || project.created_at)}` : "No activity yet"}</p>
              </div>
              <ProjectHealth project={project} />
            </div>
          </Link>
        ))}
        {!active.length && (
          <Link href="/projects" className="block rounded-md border border-dashed border-stone-200 bg-stone-50 px-3 py-4 text-sm leading-6 text-muted-foreground transition hover:bg-stone-100">
            Create or reopen a project to give Synzept a current focus.
          </Link>
        )}
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
        {!tasks.length && (
          <Link href="/tasks" className="block rounded-md border border-dashed border-stone-200 bg-stone-50 px-3 py-4 text-sm leading-6 text-muted-foreground transition hover:bg-stone-100">
            Add a task to make the next priority visible here.
          </Link>
        )}
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

function briefItem(value: Record<string, unknown> | undefined, fallbackTitle: string) {
  return {
    title: typeof value?.title === "string" && value.title ? value.title : fallbackTitle,
    detail:
      (typeof value?.detail === "string" && value.detail) ||
      (typeof value?.reason === "string" && value.reason) ||
      "",
  };
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
    "Set one concrete outcome for today.";
  const focusDetail =
    leadProject?.name ||
    dashboard?.continuity_summary ||
    leadContinuation?.description ||
    "Add projects, tasks, notes, or decisions and Synzept will connect the context.";
  const nextTitle =
    leadProject?.recommendedNextStep ||
    assistant?.recommendation.title ||
    leadTask?.title ||
    leadContinuation?.action_label ||
    "Create your next project anchor.";
  const nextDetail =
    assistant?.recommendation.detail ||
    leadContinuation?.continuation_prompt ||
    leadContinuation?.description ||
    "Synzept will use real workspace activity to recommend the next step.";
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

function getWhatMattersToday(dashboard: Dashboard | null, assistant: ContinuityAssistant | null, focusAreas: string[], personalOS: PersonalOS | null) {
  const dueTasks = (dashboard?.tasks || [])
    .filter((task) => !doneStatuses.has(task.status) && task.due_at)
    .slice(0, 3)
    .map((task) => `${task.title} (${dueLabel(task.due_at)})`);
  const projectFocus = (dashboard?.projects || [])
    .filter((project) => !doneStatuses.has(project.status))
    .slice(0, 4)
    .map((project) => project.currentFocus || project.recommendedNextStep || project.name);

  return uniqueItems([
    ...(personalOS?.top_priorities || []).map((item) => item.title),
    personalOS?.current_focus || "",
    ...focusAreas,
    ...(assistant?.priorities || []),
    ...dueTasks,
    ...projectFocus,
    "Set one concrete outcome for today.",
  ]).slice(0, 6);
}

function getReturnStats(dashboard: Dashboard | null, openLoops: string[], recentProgress: string[]) {
  return {
    updates: (dashboard?.recent_activity || []).length + (dashboard?.continuity_timeline || []).length,
    completed: recentProgress.length,
    openLoops: openLoops.length,
  };
}

function getOpenLoops({
  dashboard,
  assistant,
  priorityTasks,
  continuityItems,
  personalOS,
}: {
  dashboard: Dashboard | null;
  assistant: ContinuityAssistant | null;
  priorityTasks: Task[];
  continuityItems: ContinuityCard[];
  personalOS: PersonalOS | null;
}) {
  return uniqueItems([
    ...(personalOS?.open_loops || []).map((item) => item.title),
    ...(assistant?.open_loops || []),
    ...(dashboard?.daily?.carry_forward || []),
    ...priorityTasks.slice(0, 4).map((task) => task.title),
    ...continuityItems.filter((item) => item.type === "task").map((item) => item.title),
    "Review one unfinished thread before opening a new one.",
  ]);
}

function getRecentProgress({
  dashboard,
  assistant,
  continuityItems,
  personalOS,
}: {
  dashboard: Dashboard | null;
  assistant: ContinuityAssistant | null;
  continuityItems: ContinuityCard[];
  personalOS: PersonalOS | null;
}) {
  return uniqueItems([
    ...(personalOS?.recent_progress || []).map((item) => item.title),
    ...(personalOS?.recent_decisions || []).map((item) => item.title),
    ...(assistant?.recent_progress || []),
    ...(dashboard?.daily?.completed_today || []),
    ...(dashboard?.recent_activity || []).map((item) => item.title),
    ...continuityItems.filter((item) => item.reason).map((item) => item.reason || ""),
    "Your next completed step will become visible here.",
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

function formatShortDate(value?: string) {
  if (!value) return "recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
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

"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, ArrowUp, Loader2, MessageSquare, MoveRight } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ContinueContext, type ContinueContextCard, type Conversation, type Dashboard, type ReturnContext, type ReturnOpenLoop } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/auth";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";
const CONTINUE_PROJECT_KEY = "synzept_continue_project_id";

export function DashboardPage() {
  const router = useRouter();
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const user = useAuthStore((state) => state.user);
  const [continueContext, setContinueContext] = useState<ContinueContext | null>(null);
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .getDashboard()
      .then((data) => startTransition(() => setDashboard(data)))
      .catch(() => setError("Home could not refresh. You can still continue in Chat."))
      .finally(() => setLoading(false));
  }, [setDashboard, setLoading, startTransition]);

  useEffect(() => {
    if (dashboard && hasFreshDashboard()) return;
    load();
  }, [dashboard, hasFreshDashboard, load]);

  useEffect(() => {
    api.getContinueContext().then(setContinueContext).catch(() => setContinueContext(null));
  }, []);

  useEffect(() => {
    if (!dashboard) return;
    void api.trackEvent("home_v3_loaded", "home", {
      open_loops: dashboard.personal_os?.open_loops?.length ?? 0,
      active_projects: dashboard.personal_os?.active_projects?.length ?? dashboard.projects?.length ?? 0,
      recent_conversations: dashboard.recent_conversations?.length ?? 0,
    });
  }, [dashboard]);

  const home = useMemo(() => getHomeContext(dashboard, user?.display_name || null), [dashboard, user?.display_name]);

  const continueCard = (card: ContinueContextCard) => {
    localStorage.setItem(CHAT_DRAFT_KEY, card.prompt);
    if (card.project_id) localStorage.setItem(CONTINUE_PROJECT_KEY, card.project_id);
    void api.trackEvent("continue_card_opened", "home", {
      card_id: card.id,
      kind: card.kind,
      project_id: card.project_id,
      context_used: continueContext?.context_used ?? {},
    });
    router.push("/chat");
  };

  const continueInChat = () => {
    const text = prompt.trim() || home.suggestedAction.title;
    localStorage.setItem(CHAT_DRAFT_KEY, text);
    void api.trackEvent("home_v3_continue_to_chat", "home", { used_custom_prompt: Boolean(prompt.trim()) });
    router.push("/chat");
  };

  return (
    <PageFrame eyebrow="Home" title="Synzept">
      <div className="min-h-full bg-white text-stone-950">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
          <RecoveryBanner message={error} onRetry={load} className="mb-5" />
          {isLoading && !dashboard ? (
            <HomeSkeleton />
          ) : (
            <div className="space-y-6">
              <WelcomeHeader greeting={home.greeting} missionLine={home.missionLine} />

              <div className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
                <MissionCard mission={home.mission} whyItMatters={home.whyItMatters} progress={home.progress} />
                <FocusCard priorities={home.priorities} />
              </div>

              <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                <OpenLoopsCard loops={home.openLoops} />
                <SuggestedActionCard action={home.suggestedAction} onContinue={continueInChat} />
              </div>

              <ContinueWorkspace
                context={continueContext}
                fallbackProjects={home.recentProjects}
                fallbackConversations={home.recentConversations}
                fallbackDecisions={home.recentDecisions}
                onContinue={continueCard}
              />

              <PrimaryChatInput prompt={prompt} setPrompt={setPrompt} onContinue={continueInChat} />
            </div>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

function WelcomeHeader({ greeting, missionLine }: { greeting: string; missionLine: string }) {
  return (
    <section className="pt-2 sm:pt-5">
      <p className="text-base font-medium text-stone-500">{greeting}</p>
      <h1 className="mt-3 max-w-4xl text-4xl font-semibold leading-tight tracking-normal text-stone-950 sm:text-5xl">
        {missionLine}
      </h1>
    </section>
  );
}

function MissionCard({ mission, whyItMatters, progress }: { mission: string; whyItMatters: string; progress: HomeProgress }) {
  return (
    <HomeCard title="Current Mission" className="min-h-[260px]">
      <p className="text-2xl font-semibold leading-snug text-stone-950">{mission}</p>
      <div className="mt-6">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">Why it matters</p>
        <p className="mt-2 text-base leading-7 text-stone-600">{whyItMatters}</p>
      </div>
      <div className="mt-7">
        <div className="flex items-center justify-between gap-4">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">Progress</p>
          <p className="text-sm font-medium text-stone-700">{progress.label}</p>
        </div>
        <div className="mt-3 h-2 rounded-full bg-stone-100">
          <div className="h-2 rounded-full bg-[#3f5f4a]" style={{ width: `${progress.value}%` }} />
        </div>
        <div className="mt-4 grid gap-2 text-sm text-stone-600 sm:grid-cols-3">
          <Metric value={progress.activeProjects} label="Projects" />
          <Metric value={progress.openLoops} label="Open loops" />
          <Metric value={progress.recentMoves} label="Recent moves" />
        </div>
      </div>
    </HomeCard>
  );
}

function FocusCard({ priorities }: { priorities: HomeItem[] }) {
  return (
    <HomeCard title="Current Focus" className="min-h-[260px]">
      <div className="space-y-3">
        {priorities.map((priority, index) => (
          <LinkedRow key={`${priority.title}-${index}`} href={priority.href}>
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-950 text-xs font-semibold text-white">
              {index + 1}
            </span>
            <span className="min-w-0">
              <span className="block text-base font-medium text-stone-950">{priority.title}</span>
              {priority.detail ? <span className="mt-1 line-clamp-2 block text-sm leading-6 text-stone-500">{priority.detail}</span> : null}
            </span>
          </LinkedRow>
        ))}
      </div>
    </HomeCard>
  );
}

function OpenLoopsCard({ loops }: { loops: HomeOpenLoop[] }) {
  return (
    <HomeCard title="Open Loops" action={<span className="text-xs text-stone-400">Max 5</span>}>
      <div className="space-y-2">
        {loops.map((loop) => (
          <LinkedRow key={loop.id || loop.title} href={loop.href}>
            <span className={cn("mt-1 h-2.5 w-2.5 shrink-0 rounded-full", loop.priority === "high" ? "bg-[#9f3f3f]" : "bg-[#3f5f4a]")} />
            <span className="min-w-0">
              <span className="block text-sm font-medium text-stone-950">{loop.title}</span>
              <span className="mt-1 line-clamp-2 block text-sm leading-6 text-stone-500">
                {loop.nextStep || loop.description || loop.projectName}
              </span>
            </span>
          </LinkedRow>
        ))}
      </div>
    </HomeCard>
  );
}

function SuggestedActionCard({ action, onContinue }: { action: HomeAction; onContinue: () => void }) {
  return (
    <HomeCard title="Suggested Next Action" className="bg-[#fbfbf8]">
      <div className="flex h-full flex-col justify-between gap-6">
        <div>
          <p className="max-w-2xl text-3xl font-semibold leading-tight text-stone-950">{action.title}</p>
          {action.reason ? <p className="mt-4 max-w-2xl text-base leading-7 text-stone-600">{action.reason}</p> : null}
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          {action.href ? (
            <Link
              href={action.href}
              className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-medium text-white transition hover:bg-stone-800"
            >
              Open
              <MoveRight className="h-4 w-4" />
            </Link>
          ) : null}
          <button
            type="button"
            onClick={onContinue}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-stone-200 bg-white px-4 text-sm font-medium text-stone-900 transition hover:bg-stone-50"
          >
            Discuss in Chat
            <MessageSquare className="h-4 w-4" />
          </button>
        </div>
      </div>
    </HomeCard>
  );
}

function ContinueWorkspace({
  context,
  fallbackProjects,
  fallbackConversations,
  fallbackDecisions,
  onContinue,
}: {
  context: ContinueContext | null;
  fallbackProjects: HomeItem[];
  fallbackConversations: HomeItem[];
  fallbackDecisions: HomeItem[];
  onContinue: (card: ContinueContextCard) => void;
}) {
  const cards = context?.cards?.length ? context.cards : fallbackContinueCards(fallbackProjects, fallbackConversations, fallbackDecisions);
  return (
    <section>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">Continue System</p>
          <h2 className="mt-1 text-xl font-semibold text-stone-950">{context?.headline || "Continue where you left off"}</h2>
        </div>
      </div>
      {context?.summary ? <p className="mb-4 max-w-3xl text-sm leading-6 text-stone-500">{context.summary}</p> : null}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <ContinueCard key={card.id} card={card} onContinue={() => onContinue(card)} />
        ))}
      </div>
    </section>
  );
}

function ContinueCard({ card, onContinue }: { card: ContinueContextCard; onContinue: () => void }) {
  return (
    <article className="flex min-h-[230px] flex-col justify-between rounded-lg border border-stone-200 bg-white p-4 shadow-[0_10px_30px_rgba(32,31,28,0.05)]">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{card.last_activity}</p>
        <h3 className="mt-3 text-xl font-semibold leading-tight text-stone-950">{card.title}</h3>
        <div className="mt-4 rounded-md bg-stone-50 px-3 py-3">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-stone-400">Current status</p>
          <p className="mt-2 line-clamp-4 text-sm leading-6 text-stone-600">{card.current_status}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onContinue}
        className="mt-5 inline-flex h-11 items-center justify-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-medium text-white transition hover:bg-stone-800"
      >
        {card.continue_label || "Continue"}
        <ArrowRight className="h-4 w-4" />
      </button>
    </article>
  );
}

function PrimaryChatInput({
  prompt,
  setPrompt,
  onContinue,
}: {
  prompt: string;
  setPrompt: (value: string) => void;
  onContinue: () => void;
}) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-3 shadow-[0_14px_40px_rgba(32,31,28,0.08)]">
      <label htmlFor="continue-input" className="sr-only">
        What would you like to continue?
      </label>
      <textarea
        id="continue-input"
        rows={4}
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            onContinue();
          }
        }}
        placeholder="What would you like to continue?"
        className="min-h-32 w-full resize-none rounded-md border-0 bg-transparent px-2 py-2 text-lg leading-7 text-stone-950 outline-none placeholder:text-stone-400"
      />
      <div className="flex items-center justify-between gap-3 border-t border-stone-100 px-2 pt-3">
        <p className="hidden text-xs text-stone-500 sm:block">Synzept will continue with your mission, priorities, loops, and recent context.</p>
        <button
          type="button"
          onClick={onContinue}
          className="ml-auto inline-flex h-11 items-center justify-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-medium text-white transition hover:bg-stone-800"
        >
          Continue
          <ArrowUp className="h-4 w-4" />
        </button>
      </div>
    </section>
  );
}

function HomeCard({
  title,
  children,
  action,
  compact,
  className,
}: {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  compact?: boolean;
  className?: string;
}) {
  return (
    <section className={cn("rounded-lg border border-stone-200 bg-white shadow-[0_10px_30px_rgba(32,31,28,0.05)]", compact ? "p-4" : "p-5 sm:p-6", className)}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function LinkedRow({
  href,
  children,
  compact,
}: {
  href?: string | null;
  children: React.ReactNode;
  compact?: boolean;
}) {
  const className = cn(
    "flex min-w-0 gap-3 rounded-md border border-transparent transition",
    compact ? "px-2 py-2.5" : "px-3 py-3",
    href ? "hover:border-stone-200 hover:bg-stone-50" : "bg-white",
  );
  if (!href) return <div className={className}>{children}</div>;
  return (
    <Link href={href} className={className}>
      {children}
    </Link>
  );
}

function Metric({ value, label }: { value: number; label: string }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-2">
      <p className="text-base font-semibold text-stone-950">{value}</p>
      <p className="text-xs text-stone-500">{label}</p>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <Skeleton className="h-5 w-48 rounded-md" />
        <Skeleton className="h-24 max-w-3xl rounded-lg" />
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-lg" />
        <Skeleton className="h-64 rounded-lg" />
      </div>
      <Skeleton className="h-44 rounded-lg" />
      <div className="flex items-center gap-2 text-sm text-stone-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Preparing your continuity context
      </div>
    </div>
  );
}

type HomeItem = {
  title: string;
  detail: string;
  href?: string | null;
};

type HomeOpenLoop = {
  id: string;
  title: string;
  description: string;
  projectName: string;
  priority: string;
  href?: string | null;
  nextStep: string;
};

type HomeAction = {
  title: string;
  reason: string;
  href?: string | null;
};

type HomeProgress = {
  value: number;
  label: string;
  activeProjects: number;
  openLoops: number;
  recentMoves: number;
};

function getHomeContext(dashboard: Dashboard | null, displayName: string | null) {
  const os = dashboard?.personal_os;
  const activeProject = dashboard?.projects?.find((project) => project.status === "active") || dashboard?.projects?.[0];
  const greeting = os?.greeting || `Good morning${displayName ? `, ${displayName}` : ""}`;
  const mission =
    cleanText(os?.current_mission) ||
    cleanText(activeProject?.description) ||
    cleanText(activeProject?.name) ||
    "Build one clear place for the work that matters now.";
  const missionLine = mission.toLowerCase().startsWith("you are")
    ? mission
    : `You are building Synzept into a Continuity Operating System.`;
  const whyItMatters =
    cleanText(dashboard?.continuity_summary) ||
    cleanText(dashboard?.returning_user?.summary) ||
    "Synzept keeps mission, focus, unfinished work, and next actions visible so you can return without rebuilding context.";
  const priorities = normalizePriorities(os?.top_priorities, dashboard).slice(0, 3);
  const openLoops = normalizeOpenLoops(os?.open_loops, dashboard).slice(0, 5);
  const recentProjects = normalizeProjects(os?.active_projects, dashboard).slice(0, 4);
  const recentConversations = normalizeConversations(dashboard?.recent_conversations).slice(0, 4);
  const recentDecisions = normalizeDecisions(os?.recent_decisions).slice(0, 4);
  const suggestedAction = normalizeAction(os?.suggested_next_action, priorities[0]);
  const recentMoves = Math.max(os?.recent_progress?.length ?? 0, dashboard?.recent_activity?.length ?? 0);
  const activeProjects = dashboard?.stats?.active_projects ?? recentProjects.length;
  const openLoopCount = dashboard?.personal_os?.open_loops?.length ?? openLoops.length;
  const progressValue = Math.min(92, Math.max(18, activeProjects * 16 + Math.min(recentMoves, 5) * 8 - openLoopCount * 3));

  return {
    greeting,
    mission,
    missionLine,
    whyItMatters,
    priorities,
    openLoops,
    suggestedAction,
    recentProjects,
    recentConversations,
    recentDecisions,
    progress: {
      value: progressValue,
      label: progressValue >= 70 ? "Strong continuity" : progressValue >= 45 ? "Moving steadily" : "Needs attention",
      activeProjects,
      openLoops: openLoopCount,
      recentMoves,
    },
  };
}

function normalizePriorities(priorities: ReturnContext[] | undefined, dashboard: Dashboard | null): HomeItem[] {
  const fromOS = normalizeContexts(priorities);
  if (fromOS.length) return fromOS;
  const tasks = (dashboard?.priorities?.length ? dashboard.priorities : dashboard?.unfinished_tasks || []).slice(0, 3);
  const fromTasks = tasks.map((task) => ({
    title: task.title,
    detail: task.description || task.priority || "Priority work",
    href: "/tasks",
  }));
  if (fromTasks.length) return fromTasks;
  return [
    { title: "Review onboarding experience.", detail: "Clarify the first moment users understand Synzept.", href: "/chat" },
    { title: "Keep the current mission visible.", detail: "Anchor the workspace around what matters now.", href: "/dashboard" },
    { title: "Resolve one open loop.", detail: "Close or advance the item that is creating drag.", href: "/open-loops" },
  ];
}

function normalizeOpenLoops(loops: ReturnOpenLoop[] | undefined, dashboard: Dashboard | null): HomeOpenLoop[] {
  const mapped = (loops || []).map((loop) => ({
    id: loop.id,
    title: loop.title,
    description: loop.description || "",
    projectName: loop.project_name || "Workspace",
    priority: loop.priority || "medium",
    href: loop.href || "/open-loops",
    nextStep: loop.next_step || "",
  }));
  if (mapped.length) return mapped;
  const fallbackTask = dashboard?.priorities?.[0];
  if (fallbackTask) {
    return [
      {
        id: fallbackTask.id,
        title: fallbackTask.title,
        description: fallbackTask.description || "",
        projectName: "Workspace",
        priority: fallbackTask.priority || "medium",
        href: "/tasks",
        nextStep: fallbackTask.status || "Move this forward.",
      },
    ];
  }
  return [
    {
      id: "start",
      title: "Tell Synzept what needs attention.",
      description: "Start with one sentence.",
      projectName: "Workspace",
      priority: "medium",
      href: "/chat",
      nextStep: "Synzept will organize the next loop.",
    },
  ];
}

function normalizeContexts(items: ReturnContext[] | undefined): HomeItem[] {
  return (items || []).map((item) => ({
    title: item.title,
    detail: item.detail || "",
    href: item.href,
  }));
}

function normalizeProjects(items: ReturnContext[] | undefined, dashboard: Dashboard | null): HomeItem[] {
  const fromOS = normalizeContexts(items);
  if (fromOS.length) return fromOS;
  const projects = (dashboard?.projects || []).filter((project) => project.status !== "archived").slice(0, 4);
  const mapped = projects.map((project) => ({
    title: project.name,
    detail: project.currentFocus || project.recommendedNextStep || project.description || "Active project",
    href: `/projects/${project.id}`,
  }));
  if (mapped.length) return mapped;
  return [{ title: "Create the first project thread", detail: "Give Synzept one body of work to track.", href: "/projects" }];
}

function normalizeConversations(conversations: Conversation[] | undefined): HomeItem[] {
  const mapped = (conversations || []).map((conversation) => ({
    title: conversation.title || "Conversation",
    detail: conversation.summary || "Recent workspace thread",
    href: `/chat?conversation=${conversation.id}`,
  }));
  if (mapped.length) return mapped;
  return [{ title: "No recent conversations yet", detail: "Start from the input below.", href: "/chat" }];
}

function normalizeDecisions(items: ReturnContext[] | undefined): HomeItem[] {
  const fromOS = normalizeContexts(items);
  if (fromOS.length) return fromOS;
  return [{ title: "No recent decisions yet", detail: "Record one decision when the work moves.", href: "/chat" }];
}

function normalizeAction(action: HomeAction | undefined, fallback: HomeItem): HomeAction {
  if (action?.title) return action;
  return {
    title: fallback?.title || "Review onboarding experience.",
    reason: fallback?.detail || "This is the highest value next move Synzept can see right now.",
    href: fallback?.href || "/chat",
  };
}

function fallbackContinueCards(projects: HomeItem[], conversations: HomeItem[], decisions: HomeItem[]): ContinueContextCard[] {
  const project = projects[0];
  const conversation = conversations[0];
  const decision = decisions[0];
  const prompt = (intent: string, status: string) =>
    `${intent}\n\nLoaded continuity context:\n- Current status: ${status}\n- Recent project: ${project?.title || "No active project yet"}\n- Recent conversation: ${conversation?.title || "No recent conversation yet"}\n- Recent decision: ${decision?.title || "No recent decision yet"}\n\nDo not ask me to re-explain. Help me continue from here.`;

  return [
    {
      id: "synzept",
      kind: "synzept",
      title: "Continue Building Synzept",
      last_activity: "Ready now",
      current_status: project?.detail || "Synzept is ready to continue from your current mission.",
      continue_label: "Continue",
      href: "/chat",
      project_id: null,
      prompt: prompt("Continue building Synzept.", project?.detail || "Ready to continue."),
    },
    {
      id: "project",
      kind: "project",
      title: project ? `Continue ${project.title}` : "Continue Current Project",
      last_activity: "Recent context",
      current_status: project?.detail || "Create or choose the project Synzept should track.",
      continue_label: "Continue",
      href: "/chat",
      project_id: null,
      prompt: prompt("Continue the current project.", project?.detail || "No active project yet."),
    },
    {
      id: "goal",
      kind: "goal",
      title: "Continue Personal Goal",
      last_activity: "Current focus",
      current_status: decision?.detail || "Use the clearest goal and next action Synzept can see.",
      continue_label: "Continue",
      href: "/chat",
      project_id: null,
      prompt: prompt("Continue the most important personal goal.", decision?.detail || "Goal context is still forming."),
    },
    {
      id: "recent",
      kind: "recent",
      title: "Continue Recent Work",
      last_activity: "Latest thread",
      current_status: conversation?.detail || "Start from the most recent conversation and continue forward.",
      continue_label: "Continue",
      href: "/chat",
      project_id: null,
      prompt: prompt("Continue recent work.", conversation?.detail || "No recent thread yet."),
    },
  ];
}

function cleanText(value: string | null | undefined) {
  return value?.trim() || "";
}

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { DailyGreeting } from "@/components/daily-os/DailyGreeting";
import { HighestPriority } from "@/components/daily-os/HighestPriority";
import { Insights } from "@/components/daily-os/Insights";
import { OpenLoops } from "@/components/daily-os/OpenLoops";
import { ProgressOverview } from "@/components/daily-os/ProgressOverview";
import { QuickChat } from "@/components/daily-os/QuickChat";
import { Recommendations } from "@/components/daily-os/Recommendations";
import { RecentChanges } from "@/components/daily-os/RecentChanges";
import { DailyLayout } from "@/components/daily-os/DailyLayout";
import { api, type CalendarContext, type DailyBriefSnapshot, type Dashboard, type OpenLoopEngine, type ProactiveOverview, type Task } from "@/lib/api";
import { executeWorkflowAction, executeWorkflowFromRequest } from "@/lib/ai-workflows";
import { buildDailyExecutiveBriefExperience } from "@/lib/flagship-experiences";
import { useAuthStore } from "@/stores/auth";
import { useConnectedAppsStore } from "@/stores/connected-apps";
import { Skeleton } from "@/components/ui/skeleton";
import { RecoveryBanner } from "@/components/ui/recovery-banner";

export default function DailyBriefPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { apps, refresh } = useConnectedAppsStore();
  const [brief, setBrief] = useState<DailyBriefSnapshot | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [openLoops, setOpenLoops] = useState<OpenLoopEngine | null>(null);
  const [calendar, setCalendar] = useState<CalendarContext | null>(null);
  const [proactive, setProactive] = useState<ProactiveOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const autoPreparedRef = useRef(false);

  useEffect(() => {
    void refresh(true).catch(() => undefined);
  }, [refresh]);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [briefData, dashboardData, openLoopsData, calendarData, proactiveData] = await Promise.all([
          api.getDailyBriefV2().catch(() => null),
          api.getDashboard().catch(() => null),
          api.getOpenLoopsEngine().catch(() => null),
          api.getGoogleCalendarContext().catch(() => null),
          api.getProactiveOverview().catch(() => null),
        ]);
        if (!alive) return;
        setBrief(briefData);
        setDashboard(dashboardData);
        setOpenLoops(openLoopsData);
        setCalendar(calendarData);
        setProactive(proactiveData);
      } catch {
        if (alive) setError("Synzept could not refresh your daily brief right now. Your workspace remains safe.");
      } finally {
        if (alive) setLoading(false);
      }
    };

    void load();
    return () => {
      alive = false;
    };
  }, []);

  const view = useMemo(() => buildDailyBriefView({ brief, dashboard, openLoops, calendar, proactive, connectedApps: apps, userName: user?.display_name || user?.email || "there" }), [apps, brief, calendar, dashboard, openLoops, proactive, user?.display_name, user?.email]);
  const flagshipBrief = useMemo(() => buildDailyExecutiveBriefExperience({
    headline: view.highestPriority.title,
    recommendedFocus: view.highestPriority.reason,
    preparedDeliverables: view.recommendations.slice(0, 3).map((item) => item.title),
    openRisks: view.openLoops.slice(0, 2).map((loop) => loop.title),
    quickWins: view.progress.slice(0, 2).map((item) => item.detail),
  }), [view.highestPriority.reason, view.highestPriority.title, view.openLoops, view.progress, view.recommendations]);

  useEffect(() => {
    if (loading || autoPreparedRef.current || !view.recommendations.length) return;
    autoPreparedRef.current = true;
    void maybeAutoprepareWork(view.recommendations);
  }, [loading, view.recommendations]);

  const handlePromptSelect = async (prompt: string) => {
    void executeWorkflowFromRequest(prompt).catch(() => undefined);
    localStorage.setItem("synzept_chat_draft", prompt);
    router.push("/chat");
  };

  return (
    <main className="min-h-screen bg-surface py-8 text-stone-950">
      <div className="mx-auto max-w-7xl px-5 sm:px-8">
        <DailyLayout>
          <RecoveryBanner message={error} onRetry={() => window.location.reload()} />
          {loading ? (
            <div className="space-y-6">
              <Skeleton className="h-36 rounded-[28px]" />
              <Skeleton className="h-48 rounded-[28px]" />
              <Skeleton className="h-48 rounded-[28px]" />
            </div>
          ) : (
            <>
              <DailyGreeting name={view.userName} />

              <div className="grid gap-6 xl:grid-cols-[0.95fr_0.65fr]">
                <div className="space-y-6">
                  <HighestPriority title={view.highestPriority.title} reason={view.highestPriority.reason} impact={view.highestPriority.impact} actionLabel={view.highestPriority.actionLabel} onContinue={() => handlePromptSelect(view.highestPriority.actionPrompt)} />
                  <RecentChanges items={view.sinceLastVisit} />
                </div>

                <div className="space-y-6">
                  <ProgressOverview items={view.progress} />
                  <OpenLoops loops={view.openLoops} />
                </div>
              </div>

              <section className="rounded-[28px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#58705f]">Daily Executive Brief</p>
                    <h2 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-stone-950">{flagshipBrief.headline}</h2>
                  </div>
                  <p className="text-sm text-stone-500">Prepared from your workspace signals and calendar context.</p>
                </div>
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-[#dce5de] bg-[#f7faf7] p-4">
                    <p className="text-sm font-semibold text-stone-900">Recommended focus</p>
                    <p className="mt-2 text-sm leading-6 text-stone-700">{flagshipBrief.recommendedFocus}</p>
                  </div>
                  <div className="rounded-2xl border border-[#dce5de] bg-[#f7faf7] p-4">
                    <p className="text-sm font-semibold text-stone-900">Prepared deliverables</p>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-stone-700">
                      {flagshipBrief.preparedDeliverables.slice(0, 3).map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </div>
                </div>
              </section>

              <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
                <Insights insights={view.insights} />
                <Recommendations items={view.recommendations} onAction={async (id, actionId) => {
                  const recommendation = view.recommendations.find((item) => item.id === id);
                  if (!recommendation) return;
                  if (actionId) {
                    await executeWorkflowAction(actionId, recommendation.actions?.find((action) => action.id === actionId)?.prompt || recommendation.title);
                    return;
                  }
                  await handlePromptSelect(recommendation.title);
                }} />
              </div>

              <QuickChat prompts={view.quickChatPrompts} onPromptSelect={handlePromptSelect} />
            </>
          )}
        </DailyLayout>
      </div>
    </main>
  );
}

function buildDailyBriefView({ brief, dashboard, openLoops, calendar, proactive, connectedApps, userName }: { brief: DailyBriefSnapshot | null; dashboard: Dashboard | null; openLoops: OpenLoopEngine | null; calendar: CalendarContext | null; proactive: ProactiveOverview | null; connectedApps: Record<string, { connected?: boolean } | null>; userName: string }) {
  const thread = brief?.todaysThread;
  const primaryRecommendation = thread?.primaryRecommendation;
  const proactiveFocus = proactive?.focus?.highest_impact_action;
  const executiveBrief = proactive?.chief_of_staff?.executive_brief;
  const recommendedTitle = itemText(primaryRecommendation, "title") || itemText(brief?.recommendedNextStep, "title") || proactiveFocus?.title || dashboard?.personal_os?.suggested_next_action?.title || "Keep the next thing moving";
  const recommendedReason = [itemText(primaryRecommendation, "detail"), itemText(thread, "whyItMattersToday"), itemText(thread, "whyNow"), itemText(thread, "reasoning")].find(Boolean) || proactiveFocus?.detail || itemText(brief?.recommendedNextStep, "detail") || dashboard?.personal_os?.suggested_next_action?.reason || "This recommendation is grounded in your current context and the work that matters now.";
  const threadEvidence = (thread?.evidenceUsed || []).slice(0, 3);
  const focusWindow = thread?.bestAvailableFocusWindow;
  const focusWindowLabel = focusWindow?.minutes ? `Best focus window: ${focusWindow.minutes} min` : "";
  const recommendedImpact = focusWindowLabel || itemText(thread, "opportunityCost") || (brief?.whatMattersToday?.[0] ? itemText(brief.whatMattersToday[0], "title") || "Keeps the day aligned" : "Built from your current context");
  const upcomingTasks = (dashboard?.tasks || []).filter((task) => !isDone(task)).sort(sortByDueDate).slice(0, 3);
  const projectHealthItems = (proactive?.project_health || []).slice(0, 2).map((health, index) => ({
    id: `project-health-${index}`,
    area: health.project_title,
    detail: health.reasons[0] || "The project is being monitored for momentum and risk.",
    value: `${Math.round(health.health_score)}% health`,
  }));

  const focusItems = [
    { id: "mission", area: "Mission", detail: itemText(brief?.currentMission, "title") || itemText(brief?.currentMission, "detail") || dashboard?.personal_os?.current_mission || "Stay oriented on the work that matters most.", value: "Current mission" },
    { id: "focus", area: "Focus", detail: itemText(brief?.focusForToday, "title") || itemText(brief?.currentFocus, "title") || dashboard?.daily?.focus_areas?.[0] || "Keep one clear priority in view.", value: "Today" },
    { id: "tasks", area: "Tasks", detail: upcomingTasks[0]?.title || "No urgent tasks are visible right now.", value: `${upcomingTasks.length} open` },
    ...projectHealthItems,
  ].slice(0, 4);

  const sinceLastVisit = [
    ...(brief?.whatChanged || []).map((item, index) => ({ id: `change-${index}`, text: itemText(item, "title") || itemText(item, "detail") || "A change surfaced in your workspace.", completed: Boolean(itemText(item, "title")) })),
    ...(brief?.recentProgress || []).map((item, index) => ({ id: `progress-${index}`, text: itemText(item, "title") || itemText(item, "detail") || "Progress was captured.", completed: true })),
  ].slice(0, 6);

  const openLoopItems = (brief?.openLoops?.length ? brief.openLoops : (openLoops?.items || []))
    .filter((item) => {
      const status = itemText(item as Record<string, unknown>, "status") || itemText(item as Record<string, unknown>, "state");
      return !status || status.toLowerCase() !== "completed";
    })
    .slice(0, 4)
    .map((loop) => ({
      id: String((loop as Record<string, unknown>).id || itemText(loop as Record<string, unknown>, "sourceId") || Math.random().toString(36).slice(2)),
      title: itemText(loop as Record<string, unknown>, "title") || "Keep this loop moving",
      priority: priorityLabel(String(itemText(loop as Record<string, unknown>, "priority") || itemText(loop as Record<string, unknown>, "urgency") || "medium")) as "High" | "Medium" | "Low",
      lastUpdated: itemText(loop as Record<string, unknown>, "updatedAt") ? new Date(String(itemText(loop as Record<string, unknown>, "updatedAt"))).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "today",
      nextStep: itemText(loop as Record<string, unknown>, "nextStep") || itemText(loop as Record<string, unknown>, "detail") || "Continue from the last unfinished step.",
      detail: itemText(loop as Record<string, unknown>, "reason") || itemText(loop as Record<string, unknown>, "detail") || "This loop is still active in your current context.",
      source: itemText(loop as Record<string, unknown>, "source") || "Current context",
    }));

  const loopFallback = (dashboard?.tasks || []).filter((task) => !isDone(task)).slice(0, 3).map((task) => ({ id: task.id, title: task.title, priority: task.priority === "high" ? "High" as const : task.priority === "medium" ? "Medium" as const : "Low" as const, lastUpdated: task.updated_at ? new Date(task.updated_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "today", nextStep: task.description || "Continue from the last unfinished step.", detail: task.description || "This task is still waiting for a clear next move.", source: "Workspace tasks" }));

  const insights = [
    { id: "thread", title: "What Synzept noticed", detail: brief?.todaysThread?.whatINoticed || "Your context is clear enough for a focused recommendation." },
    ...(executiveBrief?.what_changed || []).slice(0, 2).map((entry, index) => ({ id: `change-${index}`, title: "What changed", detail: entry })),
    ...(executiveBrief?.what_matters_now || []).slice(0, 2).map((entry, index) => ({ id: `matters-${index}`, title: "What matters now", detail: entry })),
    ...(proactive?.insights || []).slice(0, 2).map((entry, index) => ({ id: `insight-${index}`, title: entry.title, detail: entry.detail })),
    ...(brief?.recentDecisions || []).slice(0, 2).map((decision, index) => ({ id: `decision-${index}`, title: itemText(decision, "title") || "Decision", detail: itemText(decision, "detail") || itemText(decision, "summary") || "This mattered enough to shape today’s direction." })),
    ...(brief?.contextToRemember || []).slice(0, 2).map((item, index) => ({ id: `memory-${index}`, title: itemText(item, "title") || "Context to remember", detail: itemText(item, "detail") || itemText(item, "summary") || "A useful signal is being kept in view for later." })),
  ].slice(0, 6);

  const connectedAppLabels = Object.entries(connectedApps || {})
    .filter(([, app]) => Boolean(app?.connected))
    .map(([provider]) => providerLabel(provider))
    .slice(0, 3);

  const recommendations = [
    {
      id: "primary",
      title: recommendedTitle,
      reason: recommendedReason,
      benefit: itemText(thread, "expectedOutcome") || "Keeps the day aligned with your strongest signal.",
      actionLabel: "Open next step",
      actionPrompt: recommendedTitle,
      whyThisExists: [
        itemText(thread, "whyItMattersToday") || "This recommendation reflects the signal that matters most right now.",
        itemText(thread, "whyNow") || "The timing matters because it is the next best move for today.",
        ...threadEvidence.map((entry) => `${entry.title}: ${entry.detail}`),
      ].filter(Boolean),
      memoriesUsed: [itemText(brief?.currentMission, "title") || "Current mission", itemText(brief?.focusForToday, "title") || "Today’s focus"].filter(Boolean),
      connectedApps: connectedAppLabels.length ? connectedAppLabels : [calendar ? "Google Calendar" : "Calendar context", brief?.todaysThread?.supportingSources?.[0] ? "Connected intelligence" : "Workspace context"].filter(Boolean),
      confidence: brief?.todaysThread?.confidence ? `${Math.round(brief.todaysThread.confidence * 100)}%` : "High",
      updatedAt: brief?.todaysThread?.generatedAt ? new Date(brief.todaysThread.generatedAt).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "today",
      actions: [
        { id: "create-outline", label: "Create outline", prompt: `Create an outline for ${recommendedTitle}` },
        { id: "review-notes", label: "Review notes", prompt: `Review the notes and context for ${recommendedTitle}` },
        { id: "schedule-block", label: "Schedule prep block", prompt: `Schedule a prep block for ${recommendedTitle}` },
      ],
    },
    ...(proactive?.recommendations || []).slice(0, 2).map((item, index) => ({
      id: `proactive-${index}`,
      title: item.title,
      reason: item.detail,
      benefit: item.priority === "high" ? "This is being prepared before it becomes urgent." : "This is the next best action surfaced from your workspace.",
      actionLabel: item.priority === "high" ? "Prepare draft" : "Review draft",
      actionPrompt: item.title,
      whyThisExists: [item.detail, item.priority === "high" ? "It surfaced as a meaningful signal from your workspace." : "It is a likely next step based on current context."],
      memoriesUsed: [item.project_id ? "Project context" : "Workspace context", "Recent activity"],
      connectedApps: connectedAppLabels.length ? connectedAppLabels : ["Workspace context"],
      confidence: item.severity === "attention" ? "High" : "Medium",
      updatedAt: "now",
      actions: [
        { id: "prepare-draft", label: "Prepare draft", prompt: item.title },
        { id: "review-context", label: "Review context", prompt: `Review the context for ${item.title}` },
      ],
    })),
    ...(brief?.todaysThread?.secondaryRecommendation ? [{
      id: "secondary",
      title: itemText(brief.todaysThread.secondaryRecommendation, "title") || "Protect the next best window",
      reason: itemText(brief.todaysThread.secondaryRecommendation, "detail") || "This is the strongest backup move if the primary plan gets interrupted.",
      benefit: itemText(thread, "prediction") || "Keeps momentum moving even if your day changes.",
      actionLabel: "Review backup plan",
      actionPrompt: itemText(brief.todaysThread.secondaryRecommendation, "title") || "Help me with the backup plan",
      whyThisExists: [itemText(thread, "opportunityCost") || "This was ranked as the next best option after the main recommendation.", "It protects momentum if the main thread gets disrupted."],
      memoriesUsed: [itemText(brief?.focusForToday, "title") || "Today’s focus", "Open loops"].filter(Boolean),
      connectedApps: connectedAppLabels.length ? connectedAppLabels : ["Workspace context"],
      confidence: "Medium",
      updatedAt: "today",
      actions: [
        { id: "plan-tomorrow", label: "Plan tomorrow", prompt: `Plan tomorrow around ${itemText(brief.todaysThread.secondaryRecommendation, "title") || "the backup plan"}` },
        { id: "review-notes", label: "Review notes", prompt: `Review the context for ${itemText(brief.todaysThread.secondaryRecommendation, "title") || "the backup plan"}` },
      ],
    }] : []),
    ...(calendar?.today || []).slice(0, 1).map((event) => ({ id: `calendar-${event.title}`, title: `Prepare for ${event.title}`, reason: event.recurring ? "A recurring event is shaping your day." : "Your calendar shows a meeting or event that may need preparation.", benefit: "Makes your next steps fit the schedule.", actionLabel: "Review schedule", actionPrompt: `Prepare for ${event.title}`, whyThisExists: [`${event.title} is on your calendar soon.`, event.recurring ? "It repeats and may need preparation." : "It is an upcoming commitment that benefits from prep."], memoriesUsed: ["Calendar context", "Recent preparation history"], connectedApps: ["Google Calendar"], confidence: "High", updatedAt: "today", actions: [
        { id: "prepare-meeting", label: "Prepare agenda", prompt: `Prepare an agenda for ${event.title}` },
        { id: "schedule-block", label: "Block focus time", prompt: `Schedule a prep block for ${event.title}` },
      ] })),
  ].slice(0, 3);

  const quickChatPrompts = [
    "Draft the next email",
    "Summarize my current project",
    "Help me plan the next 90 minutes",
    "Prepare for my upcoming meeting",
  ];

  return {
    userName: userName.split(/\s+/)[0] || "there",
    highestPriority: {
      title: recommendedTitle,
      reason: recommendedReason,
      impact: recommendedImpact,
      actionLabel: "Open next step",
      actionPrompt: recommendedTitle,
    },
    sinceLastVisit,
    progress: focusItems,
    openLoops: openLoopItems.length ? openLoopItems : loopFallback,
    insights,
    recommendations,
    quickChatPrompts,
  };
}

async function maybeAutoprepareWork(recommendations: ReturnType<typeof buildDailyBriefView>["recommendations"]) {
  const priorityMatch = recommendations.find((item) => /meeting|podcast|email|plan|review|project|draft|summar/i.test(`${item.title} ${item.reason} ${item.benefit}`));
  if (!priorityMatch) return;

  const prompt = priorityMatch.actionPrompt || priorityMatch.title;
  const key = `synzept:auto-prep:${prompt.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 80)}`;
  if (typeof window === "undefined") return;
  if (window.sessionStorage.getItem(key)) return;
  window.sessionStorage.setItem(key, "1");

  await executeWorkflowFromRequest(prompt).catch(() => undefined);
}

function providerLabel(provider: string) {
  return provider === "google_calendar" ? "Google Calendar" : provider === "google_gmail" ? "Gmail" : provider === "google_drive" ? "Google Drive" : provider === "github" ? "GitHub" : provider === "slack" ? "Slack" : provider.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function priorityLabel(priority: string) {
  const normalized = priority.toLowerCase();
  if (normalized.includes("high")) return "High";
  if (normalized.includes("medium")) return "Medium";
  return "Low";
}

function itemText(item: Record<string, unknown> | null | undefined, key: string) {
  const value = item?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function isDone(task: Task) {
  return ["completed", "done", "archived"].includes(task.status);
}

function sortByDueDate(left: Task, right: Task) {
  const leftDue = left.due_at ? new Date(left.due_at).getTime() : Number.POSITIVE_INFINITY;
  const rightDue = right.due_at ? new Date(right.due_at).getTime() : Number.POSITIVE_INFINITY;
  if (leftDue !== rightDue) return leftDue - rightDue;
  return String(left.created_at).localeCompare(String(right.created_at));
}

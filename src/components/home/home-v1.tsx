"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, CalendarDays, CheckCircle2, Compass, Mail, NotebookPen, Sparkles } from "lucide-react";
import { WorkspacePage } from "@/components/layout/workspace-content";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { PreparedArtifacts, type PreparedArtifact } from "@/components/home/PreparedArtifacts";
import { api, clearSynzeptContextCache, type ActionExecution } from "@/lib/api";
import { buildPreparationEngineOutput } from "@/lib/preparation-engine";
import { useAuthStore } from "@/stores/auth";
import { useWorkspaceStore } from "@/stores/workspace";

type ResearchStage = { label: string; status: "queued" | "running" | "completed" | "failed"; progress?: number };

export function HomeV1() {
  const user = useAuthStore((state) => state.user);
  const { dashboard, hasFreshDashboard, setDashboard } = useWorkspaceStore();
  const [loading, setLoading] = useState(!dashboard);
  const [error, setError] = useState<string | null>(null);

  const firstName = user?.display_name?.trim().split(/\s+/)[0] || user?.email?.split("@")[0] || "there";

  const engineOutput = useMemo(() => buildPreparationEngineOutput(dashboard), [dashboard]);
  const preparedArtifacts = useMemo<PreparedArtifact[]>(() => engineOutput.artifacts.map((artifact) => ({
    id: artifact.id,
    title: artifact.title,
    type: artifact.type,
    status: artifact.status === "Ready" ? "Prepared" : artifact.status === "Approved" ? "Reviewed" : artifact.status === "Reviewed" ? "Reviewed" : "Prepared",
    createdAt: artifact.created_at,
    updatedAt: artifact.created_at,
    sourceContext: artifact.summary,
    content: [
      `## Why ready`,
      artifact.why_generated,
      "",
      `## What to do next`,
      artifact.recommended_action,
      "",
      `## Evidence`,
      ...artifact.context_sources.map((source) => `- ${source}`),
    ].join("\n"),
    tags: [artifact.type.toLowerCase().replace(/\s+/g, "-"), artifact.generated_from],
    timeSavedMinutes: artifact.time_saved_minutes,
    outcomes: [artifact.summary, artifact.recommended_action],
    ctaLabel: artifact.execution_type === "approve" ? "Approve" : artifact.execution_type === "edit" ? "Edit" : artifact.execution_type === "execute" ? "Execute" : artifact.execution_type === "schedule" ? "Open" : "Review",
    sourceType: artifact.generated_from === "task_pipeline" ? "task" : "note",
    sourceId: artifact.id,
  })), [engineOutput.artifacts]);

  const completedWork = preparedArtifacts.slice(0, 4);
  const waitingForApproval = preparedArtifacts.filter((artifact) => artifact.ctaLabel === "Approve" || /review/i.test(artifact.type));
  const inProgressItems = useMemo(() => {
    const activeTasks = (dashboard?.tasks || []).filter((task) => task.title && !/completed|done|archived/i.test(task.status || ""));
    return activeTasks.slice(0, 2).map((task, index) => ({
      title: task.title,
      detail: task.description || "Continuing from your workspace context",
      progress: Math.min(95, 60 + index * 10),
      remaining: index === 0 ? "6 min left" : "12 min left",
      activity: index === 0 ? "Gathering context" : "Preparing draft",
    }));
  }, [dashboard?.tasks]);

  const router = useRouter();
  const researchInputRef = useRef<HTMLInputElement | null>(null);
  const researchSectionRef = useRef<HTMLDivElement | null>(null);

  const [actionExecutions, setActionExecutions] = useState<ActionExecution[]>([]);
  const [actionLoading, setActionLoading] = useState(false);
  const [researchQuery, setResearchQuery] = useState("");
  const [researchStatus, setResearchStatus] = useState<"idle" | "saving" | "success" | "error">("idle");
  const [researchError, setResearchError] = useState<string | null>(null);

  const loadActionExecutions = useCallback(async () => {
    setActionLoading(true);
    try {
      const executions = await api.listActionExecutions();
      setActionExecutions(executions);
    } catch {
      // keep previous execution state if refresh fails
    } finally {
      setActionLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadActionExecutions();
  }, [loadActionExecutions]);

  const openResearchInput = () => {
    researchSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    researchInputRef.current?.focus();
  };

  const quickActions = [
    { title: "Prepare Meeting", icon: CalendarDays, target: "#prepared-work" },
    { title: "Draft Email", icon: Mail, target: "#prepared-work" },
    { title: "Research Topic", icon: Compass, target: "#research-topic" },
    { title: "Plan My Day", icon: NotebookPen, target: "#prepared-work" },
  ];

  const latestResearch = useMemo(() => {
    return [...actionExecutions]
      .filter((action) => action.action_type === "research")
      .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())[0];
  }, [actionExecutions]);

  const completedResearch = latestResearch?.status === "completed" ? latestResearch : undefined;
  const activeResearch = latestResearch && latestResearch.status !== "completed" ? latestResearch : undefined;

  const sinceYouWereAway = completedWork.slice(0, 4).map((item) => ({
    title: item.title,
    detail: item.outcomes?.[0] || item.sourceContext,
  }));

  useEffect(() => {
    if (!activeResearch) return;
    const timer = window.setInterval(() => {
      void loadActionExecutions();
    }, 15_000);
    return () => window.clearInterval(timer);
  }, [activeResearch, loadActionExecutions]);

  const heroTitle = `${greeting()}, ${firstName} 👋`;
  const heroSubheading = completedWork.length ? `I've already completed ${completedWork.length} tasks for you.` : "I'm ready to take the next step for you.";
  const savedMinutes = preparedArtifacts.reduce((sum, artifact) => sum + (artifact.timeSavedMinutes || 0), 0) + (completedResearch ? 24 : 0);
  const weeklyHours = `${(engineOutput.totals.weeklyMinutes / 60).toFixed(1)} hrs`;

  const researchStages = activeResearch ? buildResearchStages(activeResearch) : [];

  return (
    <div className="min-h-full bg-[#fbfbfa] text-stone-950">
      <WorkspacePage className="max-w-[1180px] pb-24 pt-8 sm:pt-12 lg:px-12">
        <RecoveryBanner message={error} onRetry={() => window.location.reload()} />

        {loading ? (
          <HomeSkeleton />
        ) : (
          <div className="space-y-6">
            <section className="rounded-[36px] border border-[#dce5de] bg-[#f7faf7] p-6 shadow-[0_8px_24px_rgba(28,25,23,.03)] sm:p-8 lg:p-10">
              <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
                <div className="max-w-2xl">
                  <p className="text-sm font-medium uppercase tracking-[0.24em] text-[#58705f]">{formatDate(new Date())}</p>
                  <h1 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-stone-950 sm:text-5xl">{heroTitle}</h1>
                  <p className="mt-4 text-xl leading-8 text-stone-700">{heroSubheading}</p>
                  <div className="mt-6 flex flex-wrap gap-3">
                    <Link href="#prepared-work" className="inline-flex items-center gap-2 rounded-full bg-stone-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-stone-800">
                      Review Everything
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                    <Link href="#quick-actions" className="inline-flex items-center rounded-full border border-[#dce5de] bg-white px-4 py-2 text-sm font-semibold text-stone-700 transition hover:border-[#58705f] hover:text-stone-950">
                      Start New Task
                    </Link>
                  </div>
                </div>
                <div className="rounded-[24px] border border-[#dce5de] bg-white p-5 shadow-sm sm:min-w-[240px]">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-400">Today</p>
                  <p className="mt-2 text-4xl font-semibold tracking-[-0.03em] text-stone-950">{savedMinutes} min</p>
                  <p className="mt-2 text-sm leading-6 text-stone-600">saved before the day started.</p>
                </div>
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
              {latestResearch ? (
                <div className="rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] sm:p-6">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">Research employee</p>
                      <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">{latestResearch.status === "completed" ? "Research completed" : "Research in progress"}</h2>
                    </div>
                    <span className="rounded-full border border-[#dce5de] bg-[#f7faf7] px-3 py-1 text-sm font-medium text-stone-700">{latestResearch.status === "completed" ? "Saved 24 minutes" : "Background work"}</span>
                  </div>
                  <p className="mt-5 text-sm leading-6 text-stone-600">{latestResearch.title}</p>
                  <div className="mt-5 space-y-3">
                    {researchStages.map((stage) => (
                      <div key={stage.label} className="flex items-center justify-between rounded-2xl border border-[#e7eee8] bg-[#fcfdfc] px-4 py-3">
                        <div>
                          <p className="text-sm font-medium text-stone-900">{stage.label}</p>
                          {typeof stage.progress === "number" ? (
                            <p className="text-xs text-stone-500">Progress: {stage.progress}%</p>
                          ) : null}
                        </div>
                        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${stage.status === "completed" ? "bg-emerald-100 text-emerald-700" : stage.status === "running" ? "bg-amber-100 text-amber-700" : stage.status === "failed" ? "bg-red-100 text-red-700" : "bg-stone-100 text-stone-500"}`}>
                          {stage.status === "completed"
                            ? "Complete"
                            : stage.status === "running"
                            ? "Running"
                            : stage.status === "failed"
                            ? "Failed"
                            : "Queued"}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm text-stone-500">{latestResearch.request}</p>
                    <Link href={`/actions/${latestResearch.id}`} className="rounded-full bg-stone-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-stone-800">
                      Open Report
                    </Link>
                  </div>
                </div>
              ) : null}
              <div className="rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_12px_30px_rgba(28,25,23,.06)] sm:p-6">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">Completed work</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">Already handled</h2>
                  </div>
                  <span className="rounded-full border border-[#dce5de] bg-[#f7faf7] px-3 py-1 text-sm font-medium text-stone-700">{completedWork.length} ready</span>
                </div>

                <div className="mt-5 space-y-3">
                  {completedWork.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-[#dce5de] bg-[#fcfdfc] p-4 transition duration-300 hover:border-[#58705f]">
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-stone-950">{item.title}</p>
                          <p className="mt-1 text-sm leading-6 text-stone-600">{item.outcomes?.[0] || item.sourceContext}</p>
                        </div>
                        <span className="rounded-full border border-[#dce5de] bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#58705f]">{item.status}</span>
                      </div>
                      <div className="mt-4 flex items-center justify-between text-sm text-stone-600">
                        <span className="inline-flex items-center gap-2"><Sparkles className="h-4 w-4 text-[#58705f]" />{item.timeSavedMinutes || 0} min saved</span>
                        <Link href="#prepared-work" className="font-semibold text-stone-950">Review</Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_12px_30px_rgba(28,25,23,.06)] sm:p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">In progress</p>
                <div className="mt-5 space-y-4">
                  {inProgressItems.length ? inProgressItems.map((item) => (
                    <div key={item.title} className="rounded-2xl border border-[#dce5de] bg-[#f7faf7] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-stone-950">{item.title}</p>
                          <p className="mt-1 text-sm leading-6 text-stone-600">{item.activity}</p>
                        </div>
                        <span className="text-sm font-semibold text-stone-950">{item.progress}%</span>
                      </div>
                      <div className="mt-3 h-2 rounded-full bg-white">
                        <div className="h-2 rounded-full bg-[#58705f] transition-all duration-500" style={{ width: `${item.progress}%` }} />
                      </div>
                      <p className="mt-2 text-sm text-stone-500">{item.remaining}</p>
                    </div>
                  )) : <p className="text-sm leading-6 text-stone-600">Nothing is actively running right now.</p>}
                </div>
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
              <div className="rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_12px_30px_rgba(28,25,23,.06)] sm:p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">Waiting for approval</p>
                <div className="mt-5 rounded-2xl border border-[#dce5de] bg-[#fcfdfc] p-4">
                  <p className="text-sm font-semibold text-stone-950">{waitingForApproval.length} actions waiting</p>
                  <p className="mt-2 text-sm leading-6 text-stone-600">Review them in a moment or approve everything at once.</p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Link href="#prepared-work" className="rounded-full bg-stone-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-stone-800">Approve All</Link>
                    <Link href="#prepared-work" className="rounded-full border border-[#dce5de] bg-white px-4 py-2 text-sm font-semibold text-stone-700 transition hover:border-[#58705f] hover:text-stone-950">Review Individually</Link>
                  </div>
                </div>
              </div>

              <div id="quick-actions" className="rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_12px_30px_rgba(28,25,23,.06)] sm:p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">Quick actions</p>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {quickActions.map((action) => {
                    const Icon = action.icon;
                    if (action.title === "Research Topic") {
                      return (
                        <button key={action.title} type="button" onClick={openResearchInput} className="flex items-center gap-3 rounded-2xl border border-[#dce5de] bg-[#f7faf7] p-4 text-left transition hover:border-[#58705f] hover:bg-white">
                          <div className="grid h-10 w-10 place-items-center rounded-full bg-white text-[#58705f]">
                            <Icon className="h-4 w-4" />
                          </div>
                          <span className="text-sm font-semibold text-stone-950">{action.title}</span>
                        </button>
                      );
                    }
                    return (
                      <Link key={action.title} href={action.target ?? "#"} className="flex items-center gap-3 rounded-2xl border border-[#dce5de] bg-[#f7faf7] p-4 transition hover:border-[#58705f] hover:bg-white">
                        <div className="grid h-10 w-10 place-items-center rounded-full bg-white text-[#58705f]">
                          <Icon className="h-4 w-4" />
                        </div>
                        <span className="text-sm font-semibold text-stone-950">{action.title}</span>
                      </Link>
                    );
                  })}
                </div>

                <div className="mt-6 rounded-3xl border border-[#dce5de] bg-[#f7faf7] p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Research topic</p>
                      <p className="mt-2 text-sm leading-6 text-stone-600">Ask Synzept to investigate a topic and save the result as durable AI work.</p>
                    </div>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">AI employee</span>
                  </div>

                  <div id="research-topic" className="mt-5 grid gap-3 sm:grid-cols-[1.5fr_0.8fr]" ref={researchSectionRef}>
                    <input
                      ref={researchInputRef}
                      value={researchQuery}
                      onChange={(event) => setResearchQuery(event.target.value)}
                      placeholder="What should Synzept research?"
                      className="h-12 w-full rounded-2xl border border-[#dce5de] bg-white px-4 text-sm text-stone-800 outline-none transition focus:border-[#58705f] focus:ring-2 focus:ring-[#58705f]/10"
                    />
                    <button
                      type="button"
                      onClick={async () => {
                        if (!researchQuery.trim()) {
                          setResearchError("Please enter a topic to research.");
                          return;
                        }
                        setResearchError(null);
                        setResearchStatus("saving");
                        try {
                          const created = await api.createActionExecution({ request: researchQuery.trim() });
                          clearSynzeptContextCache();
                          if (created?.id) {
                            setResearchQuery("");
                            await loadActionExecutions();
                            router.push(`/actions/${created.id}`);
                            return;
                          }
                          setResearchStatus("error");
                          setResearchError("Unable to start research.");
                        } catch (error) {
                          setResearchStatus("error");
                          setResearchError(error instanceof Error ? error.message : "Unable to start research.");
                        }
                      }}
                      disabled={researchStatus === "saving"}
                      className="inline-flex h-12 items-center justify-center rounded-2xl bg-stone-950 px-4 text-sm font-semibold text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {researchStatus === "saving" ? "Queuing…" : "Research now"}
                    </button>
                  </div>

                  {researchStatus === "success" && (
                    <p className="mt-4 text-sm font-medium text-emerald-700">Research topic queued successfully. Opening the report now.</p>
                  )}
                  {researchError ? (
                    <p className="mt-4 text-sm font-medium text-red-700">{researchError}</p>
                  ) : null}
                </div>
              </div>
            </section>

            <section className="rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] sm:p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">Since you were away</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">Synzept kept moving</h2>
                </div>
                <div className="rounded-full border border-[#dce5de] bg-[#f7faf7] px-3 py-1 text-sm font-medium text-stone-700">{weeklyHours} this week</div>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {sinceYouWereAway.map((item) => (
                  <div key={item.title} className="flex items-start gap-3 rounded-2xl border border-[#dce5de] bg-[#fcfdfc] p-4">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#58705f]" />
                    <div>
                      <p className="text-sm font-semibold text-stone-950">{item.title}</p>
                      <p className="mt-1 text-sm leading-6 text-stone-600">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <PreparedArtifacts artifacts={preparedArtifacts} onRefresh={() => window.location.reload()} />
          </div>
        )}
      </WorkspacePage>
    </div>
  );
}

function buildResearchStages(action: ActionExecution): ResearchStage[] {
  const metadata = action.metadata as { research_stages?: Array<{ id?: string; label?: string; status?: string; progress?: number }> } | undefined;
  if (metadata?.research_stages?.length) {
    return metadata.research_stages.map((stage) => ({
      label: stage.label || (stage.id ? stage.id.replace("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()) : "Research stage"),
      status: stage.status === "running" || stage.status === "completed" || stage.status === "failed" ? stage.status : "queued",
      progress: typeof stage.progress === "number" ? stage.progress : undefined,
    }));
  }

  const queued = action.status === "queued";
  const running = action.status === "running";
  const completed = action.status === "completed";
  const failed = action.status === "failed" || action.status === "cancelled";

  return [
    {
      label: "Understanding objective",
      status: completed || running || failed ? "completed" : queued ? "queued" : "queued",
    },
    {
      label: "Collecting sources",
      status: running ? "running" : completed ? "completed" : failed ? "failed" : "queued",
    },
    {
      label: "Reading documents",
      status: running ? "running" : completed ? "completed" : failed ? "failed" : "queued",
    },
    {
      label: "Building report",
      status: completed ? "completed" : running ? "running" : failed ? "failed" : "queued",
    },
  ];
}

function HomeSkeleton() { return <div className="space-y-8"><div className="grid gap-3 md:grid-cols-3">{[1,2,3].map((item) => <Skeleton key={item} className="h-44 rounded-2xl" />)}</div><Skeleton className="h-56 rounded-2xl" /><div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-52 rounded-2xl" /><Skeleton className="h-52 rounded-2xl" /></div></div>; }

function greeting() { const hour = new Date().getHours(); return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening"; }
function formatDate(date: Date) { return new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(date); }

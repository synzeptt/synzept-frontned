"use client";

import { FormEvent, type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Check,
  CheckCircle2,
  Circle,
  Info,
  FolderKanban,
  Loader2,
  MessageSquareText,
  Shield,
} from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { GuidanceCard } from "@/components/ui/guidance-card";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Textarea } from "@/components/ui/textarea";
import { api, type OnboardingDashboardPreview, type OnboardingStatus } from "@/lib/api";
import { sampleDailyBrief, sampleOnboardingExamples, sampleProjectTemplates } from "@/lib/sample-data";
import { useAuthStore } from "@/stores/auth";

const STEPS = [
  { id: "welcome", label: "Welcome" },
  { id: "profile", label: "Work" },
  { id: "workspace", label: "Project" },
  { id: "brief", label: "Brief" },
  { id: "dashboard", label: "Return" },
] as const;

const COMM_STYLES = [
  { id: "concise" as const, label: "Concise", desc: "Short, direct answers" },
  { id: "balanced" as const, label: "Balanced", desc: "Clear and thoughtful" },
  { id: "deep" as const, label: "Deep", desc: "More analysis when useful" },
];

const WORK_TYPES = ["Startup", "Freelance Work", "Studies", "Content Creation", "Personal Projects"];

type StepId = (typeof STEPS)[number]["id"];

const emptyPreview: OnboardingDashboardPreview = {
  suggested_priorities: sampleOnboardingExamples.priorities,
  starter_structure: ["Create one active project", "Add one unfinished task", "Save one context note"],
  continuity_summary: "Synzept will turn your goals, priorities, and project notes into a dashboard that shows what matters next.",
  next_actions: ["Open Daily Brief", "Review open loops", "Continue the highest-impact project"],
};

export default function OnboardingPage() {
  const router = useRouter();
  const { hydrate, isAuthenticated, isLoading, user, refreshUser } = useAuthStore();
  const [step, setStep] = useState<StepId>("welcome");
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [workType, setWorkType] = useState("");
  const [goalInput, setGoalInput] = useState("");
  const [goals, setGoals] = useState<string[]>([]);
  const [priorityInput, setPriorityInput] = useState("");
  const [priorities, setPriorities] = useState<string[]>([]);
  const [commStyle, setCommStyle] = useState<"concise" | "balanced" | "deep">("balanced");

  const [projectName, setProjectName] = useState("");
  const [firstTask, setFirstTask] = useState("");
  const [firstNote, setFirstNote] = useState("");
  const [welcomeMsg, setWelcomeMsg] = useState("");
  const [finalPreview, setFinalPreview] = useState<OnboardingDashboardPreview | null>(null);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    api
      .getOnboardingStatus()
      .then((next) => {
        setStatus(next);
        if (next.is_complete) {
          router.replace("/dashboard");
          return;
        }
        setStep(toStep(next.resume_step));
        if (next.display_name) setName(next.display_name);
        if (next.goals.length) setGoals(next.goals);
      })
      .catch(() => null);
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (user?.onboarding_state === "complete") {
      router.replace("/dashboard");
    }
    if (user?.display_name) setName(user.display_name);
  }, [user, router]);

  const activeIndex = Math.max(0, STEPS.findIndex((item) => item.id === step));
  const preview = finalPreview || status?.dashboard_preview || emptyPreview;
  const completed = useMemo(() => new Set(status?.completed_steps || []), [status]);

  useEffect(() => {
    if (!isAuthenticated) return;
    api.trackEvent("onboarding_step_viewed", "onboarding", { step, active_index: activeIndex });
  }, [activeIndex, isAuthenticated, step]);

  const runStep = useCallback(async (fn: () => Promise<void>) => {
    setError(null);
    setBusy(true);
    try {
      await fn();
    } catch (err) {
      setError(recoveryMessage(err));
    } finally {
      setBusy(false);
    }
  }, []);

  const addChip = (value: string, list: string[], setList: (v: string[]) => void, clear: () => void) => {
    const v = value.trim();
    if (!v || list.length >= 5 || list.includes(v)) return;
    setList([...list, v]);
    clear();
  };

  const onWelcomeNext = () =>
    runStep(async () => {
      const next = await api.onboardingWelcome();
      setStatus(next);
      setStep("profile");
    });

  const onProfileSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Please enter your name.");
      return;
    }
    runStep(async () => {
      const next = await api.onboardingContext({
        display_name: name.trim(),
        primary_role: role.trim() || undefined,
        work_type: workType || undefined,
        goals,
        current_priorities: priorities,
        communication_style: commStyle,
      });
      setStatus(next);
      void api.trackEvent("onboarding_context_saved", "onboarding", {
        goals: goals.length,
        priorities: priorities.length,
        communication_style: commStyle,
        work_type: workType || null,
      });
      await refreshUser();
      setStep("workspace");
    });
  };

  const onWorkspaceSubmit = () =>
    runStep(async () => {
      const defaults = starterForWorkType(workType);
      const next = await api.onboardingWorkspace({
        skipped: false,
        create_project: true,
        project_name: projectName.trim() || goals[0] || defaults.name,
        project_description: defaults.description,
        first_goal: goals[0],
        first_task: firstTask.trim() || priorities[0] || defaults.recommendedNextStep,
        first_note: firstNote.trim() || sampleOnboardingExamples.firstNote,
      });
      setStatus(next);
      void api.trackEvent("onboarding_workspace_saved", "onboarding", {
        skipped: false,
        has_project_name: Boolean(projectName.trim() || goals[0]),
        has_first_task: Boolean(firstTask.trim() || priorities[0]),
        has_first_note: Boolean(firstNote.trim()),
      });
      const memoryStatus = await api.onboardingInitializeMemories();
      setStatus(memoryStatus);
      setStep("brief");
    });

  const onComplete = () =>
    runStep(async () => {
      const result = await api.onboardingComplete();
      setWelcomeMsg(result.welcome_message);
      setFinalPreview(result.dashboard_preview);
      void api.trackEvent("onboarding_completed", "onboarding", {
        tasks_created: result.tasks_created,
        memories_created: result.memories_created,
      });
      await refreshUser();
      setStep("dashboard");
    });

  const onSkipToDashboard = () =>
    runStep(async () => {
      const result = await api.onboardingSkip();
      setWelcomeMsg(result.welcome_message);
      void api.trackEvent("onboarding_skipped", "onboarding", { step });
      await refreshUser();
      router.replace("/dashboard");
    });

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-surface text-stone-950">
      <div className="mx-auto grid min-h-screen max-w-6xl gap-6 px-4 py-5 md:grid-cols-[260px_1fr] md:gap-8 md:px-8 lg:px-10">
        <aside className="flex flex-col justify-between border-border md:border-r md:py-6 md:pr-7">
          <div>
            <div className="mb-5 md:mb-8">
              <BrandLogo imageClassName="h-9" />
              <p className="mt-2 text-xs text-muted-foreground">A few choices, then a workspace that helps you continue.</p>
            </div>
            <div className="grid grid-cols-3 gap-2 md:block md:space-y-2">
              {STEPS.map((item, index) => {
                const isActive = item.id === step;
                const isDone = completed.has(item.id) || activeIndex > index;
                return (
                  <div
                    key={item.id}
                    className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm ${
                      isActive ? "bg-stone-100 text-stone-950" : "text-muted-foreground"
                    }`}
                  >
                    {isDone ? <CheckCircle2 className="h-4 w-4 text-accent" /> : <Circle className="h-4 w-4" />}
                    <span className="truncate text-[11px] sm:text-sm">{item.label}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-8 hidden rounded-md border border-border bg-white p-4 md:block">
            <p className="mb-2 flex items-center gap-2 text-xs font-medium text-stone-700">
              <Shield className="h-3.5 w-3.5 text-accent" />
              You stay in control
            </p>
            <p className="text-xs leading-5 text-muted-foreground">
              Synzept keeps only the details you choose to share. You can change them later.
            </p>
          </div>
        </aside>

        <section className="flex min-h-[640px] flex-col py-2 md:min-h-[720px] md:py-8">
          <div className="mb-6 h-1 overflow-hidden rounded-full bg-stone-100">
            <div className="h-full bg-accent transition-all" style={{ width: `${((activeIndex + 1) / STEPS.length) * 100}%` }} />
          </div>

          <RecoveryBanner message={error} className="mb-4" />

          <AnimatePresence mode="wait">
            {step === "welcome" && (
              <StepShell key="welcome">
                <div>
                  <p className="mb-3 text-sm text-accent">Welcome</p>
                  <h1 className="max-w-2xl text-3xl font-semibold md:text-5xl">Welcome to Synzept</h1>
                  <p className="mt-5 max-w-2xl text-base leading-7 text-stone-600">
                    Never lose track of your work again.
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <IntroTile icon={<Brain className="h-5 w-5" />} title="Remembers context" text="Projects, notes, decisions, and tasks stay connected." />
                  <IntroTile icon={<FolderKanban className="h-5 w-5" />} title="Tracks open loops" text="Unfinished work remains visible until you decide what happened." />
                  <IntroTile icon={<MessageSquareText className="h-5 w-5" />} title="Shows what to do next" text="Start each session from one clear recommendation." />
                </div>
                <GuidanceCard title="In the next two minutes">
                  You will choose your work type, create one starter project, see your first Daily Brief, and understand why Synzept is worth returning to tomorrow.
                </GuidanceCard>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button onClick={onWelcomeNext} disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Start setup
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                  <Button variant="ghost" onClick={onSkipToDashboard} disabled={busy}>
                    Skip setup
                  </Button>
                </div>
              </StepShell>
            )}

            {step === "profile" && (
              <StepShell key="profile">
                <form onSubmit={onProfileSubmit} className="space-y-6">
                  <StepHeading title="What are you working on?" text="Choose the closest fit. Synzept uses this to shape your starter project and first Daily Brief." />
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                    {WORK_TYPES.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => {
                          setWorkType(item);
                          const starter = starterForWorkType(item);
                          if (!goals.length) setGoals([starter.name]);
                          if (!priorities.length) setPriorities([starter.recommendedNextStep]);
                          if (!projectName) setProjectName(starter.name);
                          if (!firstTask) setFirstTask(starter.recommendedNextStep);
                        }}
                        className={`min-h-24 rounded-md border px-3 py-3 text-left text-sm transition ${
                          workType === item ? "border-accent/40 bg-accent-muted text-stone-950" : "border-border bg-white text-stone-600 hover:bg-stone-50"
                        }`}
                      >
                        <span className="font-medium">{item}</span>
                        <span className="mt-2 block text-xs leading-5 text-muted-foreground">{starterForWorkType(item).description}</span>
                      </button>
                    ))}
                  </div>
                  <GuidanceCard title="Why this matters" icon={<Info className="h-4 w-4" />}>
                    Synzept is not a blank notes app. It builds a return path around the kind of work you are doing.
                  </GuidanceCard>
                  <div className="grid gap-4 md:grid-cols-2">
                    <Field label="Display name">
                      <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Alex" />
                    </Field>
                    <Field label="Role or work type">
                      <Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Founder, student, product lead" />
                    </Field>
                  </div>
                  <ChipField
                    label="Active goals"
                    value={goalInput}
                    placeholder={sampleOnboardingExamples.goals[0]}
                    chips={goals}
                    onValue={setGoalInput}
                    onAdd={() => addChip(goalInput, goals, setGoals, () => setGoalInput(""))}
                    onRemove={(chip) => setGoals(goals.filter((item) => item !== chip))}
                  />
                  <ChipField
                    label="Current priorities"
                    value={priorityInput}
                    placeholder={sampleOnboardingExamples.priorities[0]}
                    chips={priorities}
                    onValue={setPriorityInput}
                    onAdd={() => addChip(priorityInput, priorities, setPriorities, () => setPriorityInput(""))}
                    onRemove={(chip) => setPriorities(priorities.filter((item) => item !== chip))}
                  />
                  {!goals.length && !priorities.length && (
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setGoals(sampleOnboardingExamples.goals);
                        setPriorities(sampleOnboardingExamples.priorities);
                      }}
                    >
                      Use example setup
                    </Button>
                  )}
                  <Field label="Communication style">
                    <div className="grid gap-2 md:grid-cols-3">
                      {COMM_STYLES.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          onClick={() => setCommStyle(item.id)}
                          className={`rounded-md border p-3 text-left ${
                            commStyle === item.id ? "border-accent/40 bg-accent-muted" : "border-border bg-white"
                          }`}
                        >
                          <p className="text-sm font-medium text-stone-950">{item.label}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{item.desc}</p>
                        </button>
                      ))}
                    </div>
                  </Field>
                  <Button type="submit" disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Continue to project
                  </Button>
                </form>
              </StepShell>
            )}

            {step === "workspace" && (
              <StepShell key="workspace">
                <StepHeading title="Create your first project" text="A project gives Synzept something real to remember, summarize, and help you continue." />
                <GuidanceCard title="No empty workspace">
                  Synzept will create a starter project, one visible next action, and context it can use in your first brief.
                </GuidanceCard>
                <div className="grid gap-3 md:grid-cols-3">
                  {sampleProjectTemplates.map((template) => (
                    <button
                      key={template.name}
                      type="button"
                      onClick={() => {
                        setProjectName(template.name);
                        setFirstTask(template.recommendedNextStep);
                        setFirstNote(template.description);
                      }}
                      className="rounded-md border border-border bg-white p-4 text-left transition hover:bg-stone-50"
                    >
                      <p className="text-sm font-medium text-stone-950">{template.name}</p>
                      <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted-foreground">{template.description}</p>
                    </button>
                  ))}
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="First project">
                    <Input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder={starterForWorkType(workType).name} />
                  </Field>
                  <Field label="First task">
                    <Input value={firstTask} onChange={(e) => setFirstTask(e.target.value)} placeholder={starterForWorkType(workType).recommendedNextStep} />
                  </Field>
                </div>
                <Field label="First note">
                  <Textarea
                    value={firstNote}
                    onChange={(e) => setFirstNote(e.target.value)}
                    rows={5}
                    placeholder="Anything Synzept should keep in mind about this project or season of work."
                    className="rounded-md"
                  />
                </Field>
                {!firstNote && (
                  <button
                    type="button"
                    onClick={() => setFirstNote(sampleOnboardingExamples.firstNote)}
                    className="w-fit rounded-md border border-border bg-white px-3 py-2 text-sm text-stone-700 hover:bg-stone-50"
                  >
                    Insert example note
                  </button>
                )}
                <PreviewPanel preview={preview} />
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button onClick={onWorkspaceSubmit} disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Create project and brief
                  </Button>
                </div>
              </StepShell>
            )}

            {step === "brief" && (
              <StepShell key="brief">
                <StepHeading title="Your first Daily Brief" text="Synzept turns your project into a morning view: what matters, what is unfinished, and what to do next." />
                <FirstBriefPanel projectName={projectName || starterForWorkType(workType).name} firstTask={firstTask || starterForWorkType(workType).recommendedNextStep} />
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button onClick={onComplete} disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Continue
                  </Button>
                </div>
              </StepShell>
            )}

            {step === "dashboard" && (
              <StepShell key="dashboard">
                <div className="max-w-2xl">
                  <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-md bg-accent-muted">
                    <Check className="h-7 w-7 text-accent" />
                  </div>
                  <h1 className="text-3xl font-semibold">Return tomorrow without rebuilding context.</h1>
                  <p className="mt-4 text-base leading-7 text-stone-600">
                    {welcomeMsg || "Your workspace is ready."} Synzept remembers where you left off and helps you continue from the next useful action.
                  </p>
                </div>
                <PreviewPanel preview={finalPreview || preview} />
                <GuidanceCard title="First return path">
                  Tomorrow, open Synzept and start from Today. You will see what matters, what is unfinished, and the next step without searching through old notes.
                </GuidanceCard>
                <Button onClick={() => router.replace("/dashboard")} className="w-fit">
                  Open Synzept
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </StepShell>
            )}
          </AnimatePresence>
        </section>
      </div>
    </main>
  );
}

function recoveryMessage(err: unknown) {
  const message = err instanceof Error ? err.message : "";
  if (/network|fetch|offline/i.test(message)) {
    return "Connection dropped while saving. Your entries are still on this screen; retry when the connection is back.";
  }
  if (/unauthorized|token|session|401/i.test(message)) {
    return "Your session needs to be refreshed. Sign in again and Synzept will continue from the saved onboarding step.";
  }
  return message || "Synzept could not save this step. Review the fields and try again.";
}

function toStep(value: string): StepId {
  if (value === "complete") return "dashboard";
  if (value === "memory" || value === "first_chat") return "brief";
  return STEPS.some((step) => step.id === value) ? (value as StepId) : "welcome";
}

function StepShell({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="flex flex-1 flex-col justify-center gap-7 md:gap-8"
    >
      {children}
    </motion.div>
  );
}

function StepHeading({ title, text }: { title: string; text: string }) {
  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold md:text-4xl">{title}</h1>
      <p className="mt-3 text-sm leading-6 text-stone-600 md:text-base md:leading-7">{text}</p>
    </div>
  );
}

function IntroTile({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return (
    <div className="rounded-md border border-border bg-white p-4">
      <div className="mb-4 text-accent">{icon}</div>
      <p className="text-sm font-medium">{title}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{text}</p>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

function ChipField({
  label,
  value,
  placeholder,
  chips,
  onValue,
  onAdd,
  onRemove,
}: {
  label: string;
  value: string;
  placeholder: string;
  chips: string[];
  onValue: (value: string) => void;
  onAdd: () => void;
  onRemove: (value: string) => void;
}) {
  return (
    <Field label={label}>
      <div className="flex gap-2">
        <Input
          value={value}
          onChange={(e) => onValue(e.target.value)}
          placeholder={placeholder}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onAdd();
            }
          }}
        />
        <Button type="button" variant="outline" onClick={onAdd}>
          Add
        </Button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {chips.map((chip) => (
          <button
            key={chip}
            type="button"
            className="rounded-md border border-border bg-white px-3 py-1.5 text-xs text-stone-700"
            onClick={() => onRemove(chip)}
          >
            {chip}
          </button>
        ))}
      </div>
    </Field>
  );
}

function FirstBriefPanel({ projectName, firstTask }: { projectName: string; firstTask: string }) {
  const matters = [
    projectName ? `Move ${projectName} forward` : sampleDailyBrief.whatMattersToday[0].title,
    firstTask || sampleDailyBrief.whatMattersToday[1].title,
  ];
  const loops = [
    firstTask ? `Unfinished: ${firstTask}` : sampleDailyBrief.openLoops[0].title,
    sampleDailyBrief.openLoops[1].title,
  ];

  return (
    <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">Generated now</p>
      <h2 className="mt-2 text-2xl font-semibold">What should I focus on right now?</h2>
      <div className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <BriefBlock title="What Matters Today" items={matters} />
          <BriefBlock title="Open Loops" items={loops} />
        </div>
        <div className="rounded-md border border-white/10 bg-white/5 p-4">
          <p className="text-xs font-medium uppercase text-stone-400">Recommended Next Step</p>
          <p className="mt-3 text-lg font-semibold leading-7">
            {firstTask || sampleDailyBrief.recommendedNextStep.title}
          </p>
          <p className="mt-2 text-sm leading-6 text-stone-300">
            Synzept keeps this visible so your next session starts with a clear continuation point.
          </p>
        </div>
      </div>
    </section>
  );
}

function BriefBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-4">
      <p className="text-sm font-semibold">{title}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <div key={item} className="rounded-md bg-white/10 px-3 py-2 text-sm leading-5 text-stone-100">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

function PreviewPanel({ preview }: { preview: OnboardingDashboardPreview }) {
  const priorities = preview.suggested_priorities.length ? preview.suggested_priorities : ["Choose a focus for today"];
  const structure = preview.starter_structure.length ? preview.starter_structure : ["Daily focus", "Priority queue", "Active projects"];
  return (
    <div className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]">
      <div className="rounded-md border border-border bg-white p-4">
        <p className="mb-3 text-sm font-medium">Suggested priorities</p>
        <div className="space-y-2">
          {priorities.slice(0, 4).map((item) => (
            <div key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-700">
              {item}
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-md border border-border bg-white p-4">
        <p className="mb-3 text-sm font-medium">Dashboard structure</p>
        <div className="space-y-2">
          {structure.slice(0, 5).map((item) => (
            <div key={item} className="flex items-center gap-2 text-sm text-stone-600">
              <CheckCircle2 className="h-4 w-4 text-accent" />
              {item}
            </div>
          ))}
        </div>
      </div>
      <p className="text-sm leading-6 text-muted-foreground md:col-span-2">
        {preview.continuity_summary || "Your workspace will start with today's focus, open loops, and a recommended next step."}
      </p>
    </div>
  );
}

function starterForWorkType(value: string) {
  if (value === "Freelance Work") {
    return {
      name: "Client Project",
      description: "Track deliverables, decisions, waiting items, and next steps for a client engagement.",
      recommendedNextStep: "Clarify the next client-facing deliverable.",
    };
  }
  if (value === "Studies") {
    return {
      name: "Study Plan",
      description: "Organize learning goals, notes, unfinished topics, and weekly review items.",
      recommendedNextStep: "Choose the topic that needs attention today.",
    };
  }
  if (value === "Content Creation") {
    return {
      name: "Content Pipeline",
      description: "Track ideas, drafts, publishing decisions, and follow-ups.",
      recommendedNextStep: "Pick one draft and define the next editing step.",
    };
  }
  if (value === "Personal Projects") {
    return {
      name: "Personal Project System",
      description: "Keep personal goals, open loops, and next actions easy to return to.",
      recommendedNextStep: "Choose one project to move forward this week.",
    };
  }
  return sampleProjectTemplates[0];
}

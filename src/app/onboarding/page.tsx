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
import { Markdown } from "@/components/chat/markdown";
import { Button } from "@/components/ui/button";
import { GuidanceCard } from "@/components/ui/guidance-card";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Textarea } from "@/components/ui/textarea";
import { api, type OnboardingDashboardPreview, type OnboardingStatus } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const STEPS = [
  { id: "welcome", label: "Welcome" },
  { id: "profile", label: "Profile" },
  { id: "workspace", label: "Workspace" },
  { id: "memory", label: "Memory" },
  { id: "first_chat", label: "First thread" },
  { id: "dashboard", label: "Ready" },
] as const;

const COMM_STYLES = [
  { id: "concise" as const, label: "Concise", desc: "Short, direct answers" },
  { id: "balanced" as const, label: "Balanced", desc: "Clear and thoughtful" },
  { id: "deep" as const, label: "Deep", desc: "More analysis when useful" },
];

const WORK_TYPES = ["Building", "Managing", "Studying", "Creative", "Operations"];
const MOMENTUM_FOCUS = ["Startup", "Learning", "Research", "Content creation", "Personal organization"];

type StepId = (typeof STEPS)[number]["id"];

const emptyPreview: OnboardingDashboardPreview = {
  suggested_priorities: [],
  starter_structure: [],
  continuity_summary: "",
  next_actions: [],
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
  const [aiReply, setAiReply] = useState<string | null>(null);
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
      await refreshUser();
      setStep("workspace");
    });
  };

  const onWorkspaceSubmit = (skip = false) =>
    runStep(async () => {
      const next = await api.onboardingWorkspace({
        skipped: skip,
        create_project: !skip && Boolean(projectName.trim() || goals[0] || firstTask.trim()),
        project_name: projectName.trim() || goals[0],
        first_goal: goals[0],
        first_task: firstTask.trim() || priorities[0],
        first_note: firstNote.trim() || undefined,
      });
      setStatus(next);
      setStep("memory");
      const memoryStatus = await api.onboardingInitializeMemories();
      setStatus(memoryStatus);
    });

  const onFirstChat = () =>
    runStep(async () => {
      const result = await api.onboardingFirstChat({ use_suggested_prompt: true });
      setAiReply(result.reply);
      const next = await api.getOnboardingStatus();
      setStatus(next);
      setStep("first_chat");
    });

  const onComplete = () =>
    runStep(async () => {
      const result = await api.onboardingComplete();
      setWelcomeMsg(result.welcome_message);
      setFinalPreview(result.dashboard_preview);
      await refreshUser();
      setStep("dashboard");
    });

  const onSkipToDashboard = () =>
    runStep(async () => {
      const result = await api.onboardingSkip();
      setWelcomeMsg(result.welcome_message);
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
      <div className="mx-auto grid min-h-screen max-w-6xl gap-8 px-4 py-6 md:grid-cols-[260px_1fr] md:px-8 lg:px-10">
        <aside className="flex flex-col justify-between border-border md:border-r md:py-6 md:pr-7">
          <div>
            <div className="mb-8">
              <BrandLogo imageClassName="h-9" />
              <p className="mt-2 text-xs text-muted-foreground">Setup in 2 to 4 minutes</p>
            </div>
            <div className="space-y-2">
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
                    {item.label}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-8 hidden rounded-md border border-border bg-white p-4 md:block">
            <p className="mb-2 flex items-center gap-2 text-xs font-medium text-stone-700">
              <Shield className="h-3.5 w-3.5 text-accent" />
              Clear and editable
            </p>
            <p className="text-xs leading-5 text-muted-foreground">
              Synzept uses only the context you choose to share. Profile and memory details stay editable.
            </p>
          </div>
        </aside>

        <section className="flex min-h-[720px] flex-col py-4 md:py-8">
          <div className="mb-6 h-1 overflow-hidden rounded-full bg-stone-100">
            <div className="h-full bg-accent transition-all" style={{ width: `${((activeIndex + 1) / STEPS.length) * 100}%` }} />
          </div>

          <RecoveryBanner message={error} className="mb-4" />

          <AnimatePresence mode="wait">
            {step === "welcome" && (
              <StepShell key="welcome">
                <div>
                  <p className="mb-3 text-sm text-accent">Welcome</p>
                  <h1 className="max-w-2xl text-3xl font-semibold md:text-5xl">A calm workspace for continuity.</h1>
                  <p className="mt-5 max-w-2xl text-base leading-7 text-stone-600">
                    Synzept helps organize ongoing work, useful memory, and daily focus in one place so you can return without rebuilding context.
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-3">
                  <IntroTile icon={<Brain className="h-5 w-5" />} title="Memory" text="Goals, priorities, and preferences become reusable context." />
                  <IntroTile icon={<FolderKanban className="h-5 w-5" />} title="Organization" text="Projects, notes, and tasks start connected from day one." />
                  <IntroTile icon={<MessageSquareText className="h-5 w-5" />} title="Conversation" text="Your first thread starts with the context you provide." />
                </div>
                <GuidanceCard title="How to think about setup">
                  Add only context you want Synzept to reuse: active goals, priorities, and one place where work should continue. Everything can be edited later.
                </GuidanceCard>
                <Field label="What are you working on right now?">
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {MOMENTUM_FOCUS.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setWorkType(item)}
                        className={`rounded-md border px-3 py-3 text-left text-sm transition ${
                          workType === item ? "border-accent/40 bg-accent-muted text-stone-950" : "border-border bg-white text-stone-600 hover:bg-stone-50"
                        }`}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                </Field>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button onClick={onWelcomeNext} disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Begin setup
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
                  <StepHeading title="Tell Synzept what matters" text="Keep this light. These details initialize personalization and stay editable in settings." />
                  <GuidanceCard title="What this unlocks" icon={<Info className="h-4 w-4" />}>
                    Synzept uses these details to make dashboard suggestions, memory retrieval, and conversation responses feel less generic.
                  </GuidanceCard>
                  <div className="grid gap-4 md:grid-cols-2">
                    <Field label="Display name">
                      <Input value={name} onChange={(e) => setName(e.target.value)} required placeholder="Alex" />
                    </Field>
                    <Field label="Role or work type">
                      <Input value={role} onChange={(e) => setRole(e.target.value)} placeholder="Founder, student, product lead" />
                    </Field>
                  </div>
                  <Field label="Which mode are you in most often?">
                    <div className="flex flex-wrap gap-2">
                      {[...MOMENTUM_FOCUS, ...WORK_TYPES].map((item) => (
                        <button
                          key={item}
                          type="button"
                          onClick={() => setWorkType(item)}
                          className={`rounded-md border px-3 py-2 text-sm ${
                            workType === item ? "border-accent/40 bg-accent-muted text-stone-950" : "border-border text-stone-600"
                          }`}
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </Field>
                  <ChipField
                    label="Active goals"
                    value={goalInput}
                    placeholder="Add a goal"
                    chips={goals}
                    onValue={setGoalInput}
                    onAdd={() => addChip(goalInput, goals, setGoals, () => setGoalInput(""))}
                    onRemove={(chip) => setGoals(goals.filter((item) => item !== chip))}
                  />
                  <ChipField
                    label="Current priorities"
                    value={priorityInput}
                    placeholder="This week's focus"
                    chips={priorities}
                    onValue={setPriorityInput}
                    onAdd={() => addChip(priorityInput, priorities, setPriorities, () => setPriorityInput(""))}
                    onRemove={(chip) => setPriorities(priorities.filter((item) => item !== chip))}
                  />
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
                    Continue
                  </Button>
                </form>
              </StepShell>
            )}

            {step === "workspace" && (
              <StepShell key="workspace">
                <StepHeading title="Create a starter workspace" text="Optional. One project, one task, or one note is enough to prevent an empty dashboard." />
                <GuidanceCard title="Projects are continuity anchors">
                  Use a project for any area of work you expect to revisit. Notes, tasks, conversations, and memory can then point back to the same context.
                </GuidanceCard>
                <div className="grid gap-4 md:grid-cols-2">
                  <Field label="First project">
                    <Input value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder={goals[0] || "Launch plan"} />
                  </Field>
                  <Field label="First task">
                    <Input value={firstTask} onChange={(e) => setFirstTask(e.target.value)} placeholder={priorities[0] || "Clarify next action"} />
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
                <PreviewPanel preview={preview} />
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button onClick={() => onWorkspaceSubmit(false)} disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Save starter workspace
                  </Button>
                  <Button variant="ghost" onClick={() => onWorkspaceSubmit(true)} disabled={busy}>
                    Skip workspace
                  </Button>
                </div>
              </StepShell>
            )}

            {step === "memory" && (
              <StepShell key="memory">
                <StepHeading title="Continuity foundation ready" text="Synzept has saved the goals, priorities, preferences, and work context you chose to share." />
                <GuidanceCard title="You stay in control">
                  Memory is meant to reduce repeat explanation, not trap context. You can edit, delete, pause memory, or disable personalization from Settings.
                </GuidanceCard>
                <div className="grid gap-3 md:grid-cols-2">
                  {(status?.initialized_systems || ["profile", "memory", "workspace"]).map((item) => (
                    <div key={item} className="rounded-md border border-border bg-white p-4">
                      <Check className="mb-3 h-4 w-4 text-accent" />
                      <p className="text-sm font-medium capitalize">{item.replace(/_/g, " ")}</p>
                    </div>
                  ))}
                </div>
                <PreviewPanel preview={status?.dashboard_preview || preview} />
                <Button onClick={onFirstChat} disabled={busy} className="w-fit">
                  {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Start first conversation
                </Button>
              </StepShell>
            )}

            {step === "first_chat" && (
              <StepShell key="first_chat">
                <StepHeading title="First conversation" text="This thread uses the context you just gave Synzept, so the workspace starts with continuity instead of a blank prompt." />
                <GuidanceCard title="What to try next">
                  Ask Synzept to continue a project, organize priorities, summarize what matters, or preserve a decision you do not want to lose.
                </GuidanceCard>
                {aiReply ? (
                  <div className="max-h-[420px] overflow-y-auto rounded-md border border-border bg-white p-5">
                    <Markdown content={aiReply} />
                  </div>
                ) : (
                  <div className="rounded-md border border-border bg-white p-5 text-sm leading-6 text-stone-600">
                    Your first Synzept response is ready. Continue to prepare your workspace.
                  </div>
                )}
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button onClick={onComplete} disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                    Prepare dashboard
                  </Button>
                  <Button variant="ghost" onClick={onSkipToDashboard} disabled={busy}>
                    Finish without preview
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
                  <h1 className="text-3xl font-semibold">You&apos;re set up</h1>
                  <p className="mt-4 text-base leading-7 text-stone-600">{welcomeMsg || "Your workspace is ready to continue."}</p>
                </div>
                <PreviewPanel preview={finalPreview || preview} />
                <GuidanceCard title="First return path">
                  Start from Continue Working on the dashboard. It is the fastest way back into unfinished work, open threads, and recent context.
                </GuidanceCard>
                <Button onClick={() => router.replace("/dashboard")} className="w-fit">
                  Open dashboard
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
  return STEPS.some((step) => step.id === value) ? (value as StepId) : "welcome";
}

function StepShell({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex flex-1 flex-col justify-center gap-8"
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
        {preview.continuity_summary || "Your workspace will start from onboarding context and stay useful as it grows."}
      </p>
    </div>
  );
}

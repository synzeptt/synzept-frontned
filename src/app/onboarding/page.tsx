"use client";

import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, CheckCircle2, Loader2, Pencil, Sparkles } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const QUESTIONS = [
  {
    key: "workingOn",
    label: "What are you currently working on?",
    placeholder: "Building Synzept into a continuity operating system for founders.",
  },
  {
    key: "biggestGoal",
    label: "What is your biggest goal right now?",
    placeholder: "Get the first 100 activated users and make the product feel instantly useful.",
  },
  {
    key: "strugglingWith",
    label: "What are you struggling with?",
    placeholder: "Making onboarding clear, keeping priorities focused, and turning product ideas into shipped work.",
  },
  {
    key: "continueHelp",
    label: "What would you like Synzept to help you continue?",
    placeholder: "Help me continue onboarding, home, open loops, and daily operating rhythm.",
  },
] as const;

type QuestionKey = (typeof QUESTIONS)[number]["key"];
type StepId = "capture" | "review" | "brief";

type Answers = Record<QuestionKey, string>;

type Understanding = {
  currentMission: string;
  currentFocus: string;
  openLoops: string[];
  suggestedActions: string[];
};

type WelcomeBrief = {
  currentMission?: string;
  currentFocus?: string;
  openLoops?: string[];
  suggestedFirstActions?: string[];
  topGoals?: string[];
  activeProjects?: string[];
  dailyBrief?: {
    greeting?: string;
    whatChanged?: string;
    whatMattersToday?: string;
    openLoopsRequiringAttention?: string[];
    recommendedNextAction?: string;
    focusForToday?: string;
  };
  initialWeeklyPlan?: { thisWeek?: string[]; nextWeek?: string[]; priorityFocus?: string };
};

const EMPTY_ANSWERS: Answers = {
  workingOn: "",
  biggestGoal: "",
  strugglingWith: "",
  continueHelp: "",
};

export default function OnboardingPage() {
  const router = useRouter();
  const { hydrate, isAuthenticated, isLoading, user, refreshUser } = useAuthStore();
  const [step, setStep] = useState<StepId>("capture");
  const [answers, setAnswers] = useState<Answers>(EMPTY_ANSWERS);
  const [understanding, setUnderstanding] = useState<Understanding | null>(null);
  const [welcomeBrief, setWelcomeBrief] = useState<WelcomeBrief | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.replace("/login");
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    api
      .getOnboardingStatus()
      .then((status) => {
        if (status.is_complete || user?.onboarding_state === "complete") router.replace("/dashboard");
      })
      .catch(() => null);
  }, [isAuthenticated, router, user?.onboarding_state]);

  useEffect(() => {
    if (isAuthenticated) void api.trackEvent("onboarding_2_step_viewed", "onboarding", { step });
  }, [isAuthenticated, step]);

  const completion = useMemo(() => {
    const answered = QUESTIONS.filter((question) => answers[question.key].trim()).length;
    return Math.max(12, Math.round((answered / QUESTIONS.length) * 50) + (step === "review" ? 25 : step === "brief" ? 50 : 0));
  }, [answers, step]);

  const canGenerate = QUESTIONS.every((question) => answers[question.key].trim().length >= 3);

  const run = useCallback(async (fn: () => Promise<void> | void) => {
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

  const generateUnderstanding = () => {
    if (!canGenerate) {
      setError("Answer all four questions so Synzept can build your first understanding.");
      return;
    }
    const next = buildUnderstanding(answers);
    setUnderstanding(next);
    setStep("review");
    void api.trackEvent("onboarding_2_understanding_generated", "onboarding", {
      open_loops: next.openLoops.length,
      suggested_actions: next.suggestedActions.length,
    });
  };

  const confirmUnderstanding = () =>
    run(async () => {
      const finalUnderstanding = understanding || buildUnderstanding(answers);
      const result = await api.completeFirstRunIntelligence({
        building: answers.workingOn.trim(),
        top_goals: [answers.biggestGoal.trim()],
        current_focus: finalUnderstanding.currentFocus,
        important_projects: [answers.workingOn.trim()],
        success_90_days: answers.biggestGoal.trim(),
        struggling_with: answers.strugglingWith.trim(),
        help_continue: answers.continueHelp.trim(),
        generated_current_mission: finalUnderstanding.currentMission,
        generated_open_loops: finalUnderstanding.openLoops,
        generated_suggested_actions: finalUnderstanding.suggestedActions,
      });
      setWelcomeBrief(result.welcome_brief as WelcomeBrief);
      await api.trackEvent("onboarding_2_confirmed", "onboarding", {
        open_loops: finalUnderstanding.openLoops.length,
        suggested_actions: finalUnderstanding.suggestedActions.length,
      });
      await refreshUser();
      setStep("brief");
    });

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white">
        <Loader2 className="h-8 w-8 animate-spin text-accent" />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-white text-stone-950">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-4 py-5 sm:px-6 lg:px-8">
        <header className="flex items-center justify-between gap-4">
          <BrandLogo imageClassName="h-9" />
          <div className="hidden text-right sm:block">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-stone-400">First 60 seconds</p>
            <p className="text-sm text-stone-500">Synzept learns where you are headed</p>
          </div>
        </header>

        <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-stone-100">
          <div className="h-full rounded-full bg-[#3f5f4a] transition-all duration-300" style={{ width: `${completion}%` }} />
        </div>

        <RecoveryBanner message={error} className="mt-5" />

        <section className="flex flex-1 items-center py-7 sm:py-10">
          <AnimatePresence mode="wait">
            {step === "capture" && (
              <StepShell key="capture">
                <StepHeading
                  eyebrow="Start with where you are"
                  title="Tell Synzept what you want to continue."
                  text="Four answers are enough to create your first mission, focus, open loops, suggested actions, and Daily Brief."
                />
                <div className="grid gap-4 lg:grid-cols-2">
                  {QUESTIONS.map((question) => (
                    <QuestionCard
                      key={question.key}
                      label={question.label}
                      value={answers[question.key]}
                      placeholder={question.placeholder}
                      onChange={(value) => setAnswers((current) => ({ ...current, [question.key]: value }))}
                    />
                  ))}
                </div>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <Button onClick={generateUnderstanding} disabled={busy}>
                    Create my first understanding
                    <Sparkles className="ml-2 h-4 w-4" />
                  </Button>
                  <p className="text-sm leading-6 text-stone-500">No setup maze. Just enough context to begin.</p>
                </div>
              </StepShell>
            )}

            {step === "review" && understanding && (
              <StepShell key="review">
                <StepHeading
                  eyebrow="Here's what I understand about you."
                  title="Synzept already knows the shape of your work."
                  text="Edit anything that feels off. Confirm when this matches where you are headed."
                />
                <UnderstandingEditor value={understanding} onChange={setUnderstanding} />
                <div className="flex flex-col gap-3 sm:flex-row">
                  <Button variant="outline" onClick={() => setStep("capture")} disabled={busy}>
                    <ArrowLeft className="mr-2 h-4 w-4" />
                    Back
                  </Button>
                  <Button onClick={confirmUnderstanding} disabled={busy}>
                    {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}
                    Confirm and create Daily Brief
                  </Button>
                </div>
              </StepShell>
            )}

            {step === "brief" && (
              <StepShell key="brief">
                <FirstBrief brief={welcomeBrief} fallback={understanding || buildUnderstanding(answers)} />
                <Button onClick={() => router.replace("/dashboard")}>
                  Continue to Home
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

function StepShell({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="w-full space-y-7"
    >
      {children}
    </motion.div>
  );
}

function StepHeading({ eyebrow, title, text }: { eyebrow: string; title: string; text: string }) {
  return (
    <div className="max-w-3xl">
      <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-stone-400">
        <Sparkles className="h-3.5 w-3.5" />
        {eyebrow}
      </p>
      <h1 className="mt-3 text-3xl font-semibold leading-tight tracking-normal text-stone-950 sm:text-5xl">{title}</h1>
      <p className="mt-4 max-w-2xl text-base leading-7 text-stone-600">{text}</p>
    </div>
  );
}

function QuestionCard({
  label,
  value,
  placeholder,
  onChange,
}: {
  label: string;
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block rounded-lg border border-stone-200 bg-white p-4 shadow-[0_10px_30px_rgba(32,31,28,0.05)]">
      <span className="mb-3 block text-base font-semibold text-stone-950">{label}</span>
      <Textarea
        rows={5}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="min-h-32 border-stone-200 bg-stone-50/60 text-base leading-7"
      />
    </label>
  );
}

function UnderstandingEditor({ value, onChange }: { value: Understanding; onChange: (value: Understanding) => void }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-[#fbfbf8] p-4 shadow-[0_14px_42px_rgba(32,31,28,0.07)] sm:p-5">
      <div className="mb-5 flex items-center gap-2 text-sm font-medium text-stone-600">
        <Pencil className="h-4 w-4" />
        Editable understanding
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <EditableText
          title="Current Mission"
          value={value.currentMission}
          onChange={(currentMission) => onChange({ ...value, currentMission })}
        />
        <EditableText
          title="Current Focus"
          value={value.currentFocus}
          onChange={(currentFocus) => onChange({ ...value, currentFocus })}
        />
        <EditableList
          title="First Open Loops"
          values={value.openLoops}
          onChange={(openLoops) => onChange({ ...value, openLoops })}
        />
        <EditableList
          title="First Suggested Actions"
          values={value.suggestedActions}
          onChange={(suggestedActions) => onChange({ ...value, suggestedActions })}
        />
      </div>
    </section>
  );
}

function EditableText({ title, value, onChange }: { title: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{title}</span>
      <Textarea rows={4} value={value} onChange={(event) => onChange(event.target.value)} className="bg-white text-base leading-7" />
    </label>
  );
}

function EditableList({ title, values, onChange }: { title: string; values: string[]; onChange: (values: string[]) => void }) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{title}</p>
      <div className="space-y-2">
        {values.map((item, index) => (
          <Textarea
            key={index}
            rows={2}
            value={item}
            onChange={(event) => onChange(replaceAt(values, index, event.target.value))}
            className="min-h-16 bg-white text-sm leading-6"
          />
        ))}
      </div>
    </div>
  );
}

function FirstBrief({ brief, fallback }: { brief: WelcomeBrief | null; fallback: Understanding }) {
  const mission = brief?.currentMission || fallback.currentMission;
  const focus = brief?.currentFocus || fallback.currentFocus;
  const loops = brief?.openLoops?.length ? brief.openLoops : fallback.openLoops;
  const actions = brief?.suggestedFirstActions?.length ? brief.suggestedFirstActions : fallback.suggestedActions;
  const daily = brief?.dailyBrief;
  const whatChanged = daily?.whatChanged || "Synzept created your first operating context from your answers.";
  const whatMatters = daily?.whatMattersToday || focus;
  const loopsRequiringAttention = daily?.openLoopsRequiringAttention?.length ? daily.openLoopsRequiringAttention : loops;
  const recommendedAction = daily?.recommendedNextAction || actions[0] || focus;
  const focusForToday = daily?.focusForToday || brief?.initialWeeklyPlan?.priorityFocus || focus;

  return (
    <section className="rounded-lg bg-stone-950 p-5 text-white shadow-[0_18px_60px_rgba(32,31,28,0.18)] sm:p-7">
      <p className="text-xs font-medium uppercase tracking-[0.16em] text-stone-400">{daily?.greeting || "Good Morning"}</p>
      <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight tracking-normal sm:text-5xl">
        Your first Daily Brief is ready.
      </h1>
      <p className="mt-4 max-w-3xl text-lg leading-8 text-stone-100">{mission}</p>
      <div className="mt-7 grid gap-3 lg:grid-cols-2">
        <BriefBlock title="What Changed" items={[whatChanged]} />
        <BriefBlock title="What Matters Today" items={[whatMatters]} />
        <BriefBlock title="Open Loops Requiring Attention" items={loopsRequiringAttention} />
        <BriefBlock title="Recommended Next Action" items={[recommendedAction]} />
        <BriefBlock title="Focus For Today" items={[focusForToday]} />
        <BriefBlock title="Suggested Actions" items={actions} />
      </div>
    </section>
  );
}

function BriefBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-4">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 5).map((item) => (
          <p key={item} className="text-sm leading-6 text-stone-100">{item}</p>
        ))}
      </div>
    </div>
  );
}

function buildUnderstanding(answers: Answers): Understanding {
  const workingOn = answers.workingOn.trim();
  const goal = answers.biggestGoal.trim();
  const struggle = answers.strugglingWith.trim();
  const continueHelp = answers.continueHelp.trim();

  return {
    currentMission: `Turn ${workingOn} into progress toward ${goal}.`,
    currentFocus: continueHelp || `Move ${workingOn} forward without losing focus.`,
    openLoops: compactList([
      `Clarify the next concrete step for ${workingOn}.`,
      `Resolve the main struggle: ${struggle}.`,
      `Define what progress toward ${goal} looks like this week.`,
    ]),
    suggestedActions: compactList([
      `Spend 25 minutes on: ${continueHelp || workingOn}.`,
      `Write the next visible milestone for ${goal}.`,
      `Identify one blocker inside: ${struggle}.`,
    ]),
  };
}

function replaceAt(values: string[], index: number, value: string) {
  return values.map((item, itemIndex) => (itemIndex === index ? value : item));
}

function compactList(values: string[]) {
  return Array.from(new Set(values.map((item) => item.trim()).filter(Boolean)));
}

function recoveryMessage(err: unknown) {
  const message = err instanceof Error ? err.message : "";
  if (/network|fetch|offline/i.test(message)) return "Connection dropped while saving. Your answers are still here; retry when the connection is back.";
  if (/unauthorized|token|session|401/i.test(message)) return "Your session needs to be refreshed. Sign in again and Synzept will continue onboarding.";
  return message || "Synzept could not create your first Daily Brief. Review the understanding and try again.";
}

"use client";

import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, ArrowRight, CheckCircle2, Circle, Loader2, Plus, Sparkles, Target, X } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";

const STEPS = [
  { id: "building", label: "Building" },
  { id: "goals", label: "Goals" },
  { id: "focus", label: "Focus" },
  { id: "projects", label: "Projects" },
  { id: "success", label: "90 Days" },
  { id: "brief", label: "Brief" },
] as const;

type StepId = (typeof STEPS)[number]["id"];

type WelcomeBrief = {
  currentMission?: string;
  currentFocus?: string;
  topGoals?: string[];
  activeProjects?: string[];
  openLoops?: string[];
  suggestedFirstActions?: string[];
  initialWeeklyPlan?: { thisWeek?: string[]; nextWeek?: string[]; priorityFocus?: string };
  success90Days?: string;
};

export default function OnboardingPage() {
  const router = useRouter();
  const { hydrate, isAuthenticated, isLoading, user, refreshUser } = useAuthStore();
  const [step, setStep] = useState<StepId>("building");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [welcomeBrief, setWelcomeBrief] = useState<WelcomeBrief | null>(null);

  const [building, setBuilding] = useState("");
  const [goals, setGoals] = useState<string[]>(["", "", ""]);
  const [currentFocus, setCurrentFocus] = useState("");
  const [projects, setProjects] = useState<string[]>([""]);
  const [success90Days, setSuccess90Days] = useState("");

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [isAuthenticated, isLoading, router]);

  useEffect(() => {
    if (!isAuthenticated) return;
    api
      .getOnboardingStatus()
      .then((status) => {
        if (status.is_complete || user?.onboarding_state === "complete") {
          router.replace("/dashboard");
          return;
        }
        if (status.goals.length) setGoals(padList(status.goals.slice(0, 3), 3));
      })
      .catch(() => null);
  }, [isAuthenticated, router, user?.onboarding_state]);

  useEffect(() => {
    if (isAuthenticated) void api.trackEvent("first_run_step_viewed", "onboarding", { step });
  }, [isAuthenticated, step]);

  const activeIndex = Math.max(0, STEPS.findIndex((item) => item.id === step));
  const cleanGoals = useMemo(() => compactList(goals), [goals]);
  const cleanProjects = useMemo(() => compactList(projects), [projects]);
  const firstAction = useMemo(() => suggestedFirstAction(building, currentFocus, cleanGoals, cleanProjects), [building, cleanGoals, cleanProjects, currentFocus]);

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

  const goNext = (next: StepId) => {
    setError(null);
    setStep(next);
  };

  const finish = () =>
    run(async () => {
      if (!building.trim()) throw new Error("Tell Synzept what you are building.");
      if (!cleanGoals.length) throw new Error("Add at least one top goal.");
      if (!currentFocus.trim()) throw new Error("Add your current focus.");
      if (!cleanProjects.length) throw new Error("Add at least one important project.");
      if (!success90Days.trim()) throw new Error("Add what would make the next 90 days successful.");

      const result = await api.completeFirstRunIntelligence({
        building: building.trim(),
        top_goals: cleanGoals,
        current_focus: currentFocus.trim(),
        important_projects: cleanProjects,
        success_90_days: success90Days.trim(),
      });
      setWelcomeBrief(result.welcome_brief as WelcomeBrief);
      await api.trackEvent("first_run_intelligence_completed", "onboarding", {
        goals: cleanGoals.length,
        projects: cleanProjects.length,
      });
      await refreshUser();
      goNext("brief");
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
      <div className="mx-auto grid min-h-screen max-w-6xl gap-6 px-4 py-5 md:grid-cols-[250px_1fr] md:gap-8 md:px-8 lg:px-10">
        <aside className="flex flex-col justify-between border-border md:border-r md:py-6 md:pr-7">
          <div>
            <div className="mb-5 md:mb-8">
              <BrandLogo imageClassName="h-9" />
              <p className="mt-2 text-xs leading-5 text-muted-foreground">Answer five questions. Synzept will create your first mission, projects, open loops, and weekly plan.</p>
            </div>
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-6 md:block md:space-y-2">
              {STEPS.map((item, index) => {
                const isActive = item.id === step;
                const isDone = activeIndex > index;
                return (
                  <div key={item.id} className={`flex items-center gap-2 rounded-md px-2.5 py-2 text-sm md:gap-3 md:px-3 ${isActive ? "bg-stone-100 text-stone-950" : "text-muted-foreground"}`}>
                    {isDone ? <CheckCircle2 className="h-4 w-4 shrink-0 text-accent" /> : <Circle className="h-4 w-4 shrink-0" />}
                    <span className="truncate text-[11px] sm:text-xs md:text-sm">{item.label}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-8 hidden rounded-md border border-border bg-white p-4 md:block">
            <p className="mb-2 flex items-center gap-2 text-xs font-medium text-stone-700">
              <Target className="h-3.5 w-3.5 text-accent" />
              First-run intelligence
            </p>
            <p className="text-xs leading-5 text-muted-foreground">Your answers become editable memory, projects, goals, and open loops.</p>
          </div>
        </aside>

        <section className="flex min-h-[680px] flex-col py-2 md:min-h-[760px] md:py-8">
          <div className="mb-6 h-1 overflow-hidden rounded-full bg-stone-100">
            <div className="h-full bg-accent transition-all" style={{ width: `${((activeIndex + 1) / STEPS.length) * 100}%` }} />
          </div>

          <RecoveryBanner message={error} className="mb-4" />

          <AnimatePresence mode="wait">
            {step === "building" && (
              <StepShell key="building">
                <StepHeading title="What are you building?" text="Name the work Synzept should organize around. This becomes your first Current Mission." />
                <Textarea rows={6} value={building} onChange={(event) => setBuilding(event.target.value)} placeholder="I am building Synzept into a personal intelligence system for founders." />
                <StepActions onNext={() => building.trim() ? goNext("goals") : setError("Tell Synzept what you are building.")} nextLabel="Continue" />
              </StepShell>
            )}

            {step === "goals" && (
              <StepShell key="goals">
                <StepHeading title="What are your top goals?" text="These become your top goals and initial priority context." />
                <FixedListEditor values={goals} placeholders={["Get 100 paying users", "Launch V1", "Improve onboarding"]} onChange={setGoals} />
                <StepActions onBack={() => goNext("building")} onNext={() => cleanGoals.length ? goNext("focus") : setError("Add at least one top goal.")} nextLabel="Continue" />
              </StepShell>
            )}

            {step === "focus" && (
              <StepShell key="focus">
                <StepHeading title="What are you focused on right now?" text="This becomes Current Focus and drives the suggested next action." />
                <Textarea rows={6} value={currentFocus} onChange={(event) => setCurrentFocus(event.target.value)} placeholder="Finishing payments, onboarding, and the founder dashboard." />
                <StepActions onBack={() => goNext("goals")} onNext={() => currentFocus.trim() ? goNext("projects") : setError("Add your current focus.")} nextLabel="Continue" />
              </StepShell>
            )}

            {step === "projects" && (
              <StepShell key="projects">
                <StepHeading title="What projects matter most?" text="Synzept will create these as active projects with focus and next-step context." />
                <DynamicListEditor values={projects} placeholder="Synzept Launch" onChange={setProjects} addLabel="Add project" />
                <StepActions onBack={() => goNext("focus")} onNext={() => cleanProjects.length ? goNext("success") : setError("Add at least one important project.")} nextLabel="Continue" />
              </StepShell>
            )}

            {step === "success" && (
              <StepShell key="success">
                <StepHeading title="What would make the next 90 days successful?" text="Synzept will use this to judge priorities, risks, and progress." />
                <Textarea rows={7} value={success90Days} onChange={(event) => setSuccess90Days(event.target.value)} placeholder="100 paying users, a reliable onboarding path, and weekly customer conversations." />
                <PreviewPanel title="Suggested first action" items={[firstAction]} />
                <StepActions onBack={() => goNext("projects")} onNext={finish} nextLabel={busy ? "Building workspace" : "Build my workspace"} disabled={busy} />
              </StepShell>
            )}

            {step === "brief" && (
              <StepShell key="brief">
                <AgentBrief brief={welcomeBrief} fallback={{ building, goals: cleanGoals, projects: cleanProjects, focus: currentFocus, firstAction, success90Days }} />
                <Button onClick={() => router.replace("/dashboard")}>
                  Open Personal OS
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
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.2, ease: "easeOut" }} className="flex flex-1 flex-col justify-center gap-7 md:gap-8">
      {children}
    </motion.div>
  );
}

function StepHeading({ title, text }: { title: string; text: string }) {
  return (
    <div className="max-w-2xl">
      <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-muted">
        <Sparkles className="h-3.5 w-3.5" />
        First-run setup
      </p>
      <h1 className="mt-3 text-2xl font-semibold md:text-4xl">{title}</h1>
      <p className="mt-3 text-sm leading-6 text-stone-600 md:text-base md:leading-7">{text}</p>
    </div>
  );
}

function StepActions({ onBack, onNext, nextLabel, disabled = false }: { onBack?: () => void; onNext: () => void; nextLabel: string; disabled?: boolean }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row">
      {onBack && (
        <Button variant="outline" onClick={onBack} disabled={disabled}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      )}
      <Button onClick={onNext} disabled={disabled}>
        {disabled ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        {nextLabel}
        {!disabled ? <ArrowRight className="ml-2 h-4 w-4" /> : null}
      </Button>
    </div>
  );
}

function FixedListEditor({ values, placeholders, onChange }: { values: string[]; placeholders: string[]; onChange: (values: string[]) => void }) {
  return (
    <div className="grid gap-3">
      {values.map((value, index) => (
        <label key={index} className="block">
          <span className="mb-2 block text-xs font-medium text-muted-foreground">Goal {index + 1}</span>
          <Input value={value} onChange={(event) => onChange(replaceAt(values, index, event.target.value))} placeholder={placeholders[index]} />
        </label>
      ))}
    </div>
  );
}

function DynamicListEditor({ values, placeholder, onChange, addLabel }: { values: string[]; placeholder: string; onChange: (values: string[]) => void; addLabel: string }) {
  const rows = values.length ? values : [""];
  return (
    <div className="space-y-3">
      {rows.map((value, index) => (
        <div key={index} className="flex gap-2">
          <Input value={value} onChange={(event) => onChange(replaceAt(rows, index, event.target.value))} placeholder={index === 0 ? placeholder : "Add another"} />
          {rows.length > 1 ? (
            <Button type="button" variant="outline" size="icon" aria-label="Remove item" onClick={() => onChange(rows.filter((_, itemIndex) => itemIndex !== index))}>
              <X className="h-4 w-4" />
            </Button>
          ) : null}
        </div>
      ))}
      <Button type="button" variant="outline" onClick={() => onChange([...rows, ""])}>
        <Plus className="mr-2 h-4 w-4" />
        {addLabel}
      </Button>
    </div>
  );
}

function PreviewPanel({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-md border border-border bg-white p-4">
      <p className="text-sm font-medium text-stone-950">{title}</p>
      <div className="mt-3 space-y-2">
        {items.map((item) => (
          <p key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-700">{item}</p>
        ))}
      </div>
    </section>
  );
}

function AgentBrief({
  brief,
  fallback,
}: {
  brief: WelcomeBrief | null;
  fallback: { building: string; goals: string[]; projects: string[]; focus: string; firstAction: string; success90Days: string };
}) {
  const mission = brief?.currentMission || `Build ${fallback.building}`;
  const focus = brief?.currentFocus || fallback.focus;
  const goals = brief?.topGoals?.length ? brief.topGoals : fallback.goals;
  const projects = brief?.activeProjects?.length ? brief.activeProjects : fallback.projects;
  const actions = brief?.suggestedFirstActions?.length ? brief.suggestedFirstActions : [fallback.firstAction];
  const loops = brief?.openLoops || [];

  return (
    <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft md:p-7">
      <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-stone-400">
        <Sparkles className="h-3.5 w-3.5" />
        Welcome Brief
      </p>
      <h1 className="mt-3 text-3xl font-semibold leading-tight md:text-5xl">{mission}</h1>
      <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-300">Synzept created your first workspace around your goals, active projects, open loops, and initial weekly plan.</p>
      <div className="mt-6 grid gap-3 md:grid-cols-2">
        <BriefBlock title="Current Focus" items={[focus]} />
        <BriefBlock title="Top Goals" items={goals} />
        <BriefBlock title="Active Projects" items={projects} />
        <BriefBlock title="Suggested First Actions" items={actions} />
        <BriefBlock title="Open Loops" items={loops.length ? loops : [`Track 90-day success: ${fallback.success90Days}`]} />
        <BriefBlock title="Initial Weekly Plan" items={[brief?.initialWeeklyPlan?.priorityFocus || focus, ...(brief?.initialWeeklyPlan?.thisWeek || []).slice(0, 3)]} />
      </div>
    </section>
  );
}

function BriefBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md border border-white/10 bg-white/5 p-4">
      <p className="text-xs font-medium uppercase text-stone-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 5).map((item) => (
          <p key={item} className="text-sm leading-6 text-stone-100">{item}</p>
        ))}
      </div>
    </div>
  );
}

function replaceAt(values: string[], index: number, value: string) {
  return values.map((item, itemIndex) => (itemIndex === index ? value : item));
}

function compactList(values: string[]) {
  return Array.from(new Set(values.map((item) => item.trim()).filter(Boolean)));
}

function padList(values: string[], length: number) {
  return [...values, ...Array.from({ length }, () => "")].slice(0, length);
}

function suggestedFirstAction(building: string, focus: string, goals: string[], projects: string[]) {
  const anchor = focus.trim() || goals[0] || projects[0] || building.trim() || "your main goal";
  return `Spend 25 minutes turning "${anchor}" into the next concrete action.`;
}

function recoveryMessage(err: unknown) {
  const message = err instanceof Error ? err.message : "";
  if (/network|fetch|offline/i.test(message)) return "Connection dropped while saving. Your entries are still here; retry when the connection is back.";
  if (/unauthorized|token|session|401/i.test(message)) return "Your session needs to be refreshed. Sign in again and Synzept will continue onboarding.";
  return message || "Synzept could not build your first workspace. Review the fields and try again.";
}

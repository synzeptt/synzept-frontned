"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { OnboardingLayout } from "@/components/onboarding/OnboardingLayout";
import { WelcomeScreen } from "@/components/onboarding/WelcomeScreen";
import { ProgressHeader } from "@/components/onboarding/ProgressHeader";
import { OptionCard } from "@/components/onboarding/OptionCard";
import { GoalSelector } from "@/components/onboarding/GoalSelector";
import { InterestSelector } from "@/components/onboarding/InterestSelector";
import { ProjectInput } from "@/components/onboarding/ProjectInput";
import { SummaryScreen } from "@/components/onboarding/SummaryScreen";
import { CompletionScreen } from "@/components/onboarding/CompletionScreen";
import {
  onboardingGoals,
  onboardingPlanningStyles,
  onboardingPreferences,
  onboardingRoles,
  onboardingSampleProjects,
  onboardingTimeOfDay,
} from "@/data/onboardingMock";
import type {
  OnboardingGoal,
  OnboardingPlanningStyle,
  OnboardingPreference,
  OnboardingProject,
  OnboardingRole,
  OnboardingTimeOfDay,
} from "@/types/onboarding";

const TOTAL_STEPS = 8;

type Step =
  | "welcome"
  | "role"
  | "goals"
  | "projects"
  | "help"
  | "workStyle"
  | "summary"
  | "completion";

export default function OnboardingNewPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("welcome");
  const [role, setRole] = useState<OnboardingRole | undefined>(undefined);
  const [goals, setGoals] = useState<OnboardingGoal[]>([]);
  const [projects, setProjects] = useState<OnboardingProject[]>([]);
  const [projectName, setProjectName] = useState("");
  const [preferences, setPreferences] = useState<OnboardingPreference[]>([]);
  const [timeOfDay, setTimeOfDay] = useState<OnboardingTimeOfDay | undefined>(undefined);
  const [planningStyle, setPlanningStyle] = useState<OnboardingPlanningStyle | undefined>(undefined);

  const currentStepIndex = useMemo(
    () => ["welcome", "role", "goals", "projects", "help", "workStyle", "summary", "completion"].indexOf(step) + 1,
    [step],
  );

  const handleToggleGoal = (goal: OnboardingGoal) => {
    setGoals((current) =>
      current.includes(goal) ? current.filter((item) => item !== goal) : [...current, goal],
    );
  };

  const handleTogglePreference = (preference: OnboardingPreference) => {
    setPreferences((current) =>
      current.includes(preference) ? current.filter((item) => item !== preference) : [...current, preference],
    );
  };

  const handleAddProject = () => {
    if (!projectName.trim()) return;
    setProjects((current) => [...current, { id: crypto.randomUUID(), name: projectName.trim() }]);
    setProjectName("");
  };

  const handleRemoveProject = (id: string) => {
    setProjects((current) => current.filter((project) => project.id !== id));
  };

  const handleAddSampleProject = (name: string) => {
    if (!name || projects.some((project) => project.name === name)) return;
    setProjects((current) => [...current, { id: crypto.randomUUID(), name }]);
  };

  return (
    <OnboardingLayout>
      <div className="mx-auto flex min-h-screen max-w-4xl flex-col gap-6 py-8">
        <ProgressHeader step={currentStepIndex} total={TOTAL_STEPS} label="Onboarding" />

      {step === "welcome" && <WelcomeScreen onBegin={() => setStep("role")} />}

      {step === "role" && (
        <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-soft">
          <div className="space-y-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">Who are you?</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950">What best describes you?</h1>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {onboardingRoles.map((option) => (
                <OptionCard
                  key={option}
                  label={option}
                  selected={role === option}
                  onSelect={() => setRole(option)}
                />
              ))}
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button onClick={() => setStep("welcome")} variant="outline">Back</Button>
              <Button onClick={() => setStep("goals")} disabled={!role}>Continue</Button>
            </div>
          </div>
        </section>
      )}

      {step === "goals" && (
        <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-soft">
          <div className="space-y-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">Goals</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950">What are you trying to achieve?</h1>
            </div>
            <GoalSelector goals={onboardingGoals} selectedGoals={goals} onToggleGoal={handleToggleGoal} />
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button onClick={() => setStep("role")} variant="outline">Back</Button>
              <Button onClick={() => setStep("projects")} disabled={goals.length === 0}>Continue</Button>
            </div>
          </div>
        </section>
      )}

      {step === "projects" && (
        <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-soft">
          <div className="space-y-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">Current projects</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950">What are you working on right now?</h1>
            </div>
            <ProjectInput
              projects={projects}
              projectName={projectName}
              onProjectNameChange={setProjectName}
              onAddProject={handleAddProject}
              onRemoveProject={handleRemoveProject}
            />
            <div className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
              <p className="text-sm font-semibold text-stone-900">Example projects</p>
              <div className="mt-4 flex flex-wrap gap-3">
                {onboardingSampleProjects.map((project) => (
                  <button
                    key={project.id}
                    type="button"
                    onClick={() => handleAddSampleProject(project.name)}
                    className="rounded-2xl border border-stone-200 bg-white px-4 py-2 text-sm text-stone-700 shadow-sm transition hover:bg-stone-50 focus:outline-none focus:ring-2 focus:ring-accent/30"
                  >
                    {project.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button onClick={() => setStep("goals")} variant="outline">Back</Button>
              <Button onClick={() => setStep("help")} disabled={projects.length === 0}>Continue</Button>
            </div>
          </div>
        </section>
      )}

      {step === "help" && (
        <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-soft">
          <div className="space-y-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">How should Synzept help?</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950">Choose the ways Synzept can support you.</h1>
            </div>
            <InterestSelector
              preferences={onboardingPreferences}
              selectedPreferences={preferences}
              onTogglePreference={handleTogglePreference}
            />
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button onClick={() => setStep("projects")} variant="outline">Back</Button>
              <Button onClick={() => setStep("workStyle")} disabled={preferences.length === 0}>Continue</Button>
            </div>
          </div>
        </section>
      )}

      {step === "workStyle" && (
        <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-soft">
          <div className="space-y-6">
            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">Work style</p>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950">How do you usually work?</h1>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-4">
                <p className="text-sm font-semibold text-stone-900">Time of day</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  {onboardingTimeOfDay.map((option) => (
                    <OptionCard
                      key={option}
                      label={option}
                      selected={timeOfDay === option}
                      onSelect={() => setTimeOfDay(option)}
                    />
                  ))}
                </div>
              </div>
              <div className="space-y-4">
                <p className="text-sm font-semibold text-stone-900">Preferred planning style</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  {onboardingPlanningStyles.map((option) => (
                    <OptionCard
                      key={option}
                      label={option}
                      selected={planningStyle === option}
                      onSelect={() => setPlanningStyle(option)}
                    />
                  ))}
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Button onClick={() => setStep("help")} variant="outline">Back</Button>
              <Button onClick={() => setStep("summary")} disabled={!timeOfDay || !planningStyle}>Continue</Button>
            </div>
          </div>
        </section>
      )}

      {step === "summary" && (
        <SummaryScreen
          role={role}
          goals={goals}
          projects={projects}
          preferences={preferences}
          timeOfDay={timeOfDay}
          planningStyle={planningStyle}
          onEdit={() => setStep("role")}
          onComplete={() => setStep("completion")}
        />
      )}

      {step === "completion" && (
        <CompletionScreen onEnter={() => router.push("/dashboard")} />
      )}

      <div className="flex items-center justify-between text-sm text-stone-500">
        <p>{step === "welcome" ? "Welcome" : `Step ${currentStepIndex} of ${TOTAL_STEPS}`}</p>
        <p>{step === "completion" ? "Ready to begin" : `Keep it simple and intentional.`}</p>
      </div>
    </div>
  </OnboardingLayout>
  );
}

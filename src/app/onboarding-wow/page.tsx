"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Sparkles, CheckCircle2, ChevronRight, Compass, CircleDashed } from "lucide-react";

const steps = [
  { id: "welcome", title: "Welcome", detail: "Show the difference immediately." },
  { id: "interview", title: "Smart interview", detail: "Learn enough in seconds." },
  { id: "reasoning", title: "AI reasoning", detail: "Turn context into momentum." },
  { id: "results", title: "First wow", detail: "Surface the mission and next action." },
];

export default function OnboardingWowPage() {
  const [screen, setScreen] = useState<"welcome" | "interview" | "reasoning" | "results">("welcome");
  const [focusArea, setFocusArea] = useState("");
  const [goal, setGoal] = useState("");
  const [completed, setCompleted] = useState(false);

  const progress = useMemo(() => {
    if (screen === "welcome") return 10;
    if (screen === "interview") return 35;
    if (screen === "reasoning") return 70;
    return 100;
  }, [screen]);

  useEffect(() => {
    if (screen === "reasoning") {
      const timeout = window.setTimeout(() => setScreen("results"), 900);
      return () => window.clearTimeout(timeout);
    }
  }, [screen]);

  const handleContinue = () => {
    if (screen === "welcome") {
      setScreen("interview");
      return;
    }
    if (screen === "interview") {
      setScreen("reasoning");
      return;
    }
    if (screen === "results") {
      setCompleted(true);
    }
  };

  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">10-Minute Wow</p>
              <h1 className="text-3xl font-semibold">Turn first-run curiosity into immediate clarity</h1>
            </div>
            <div className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-sm text-stone-600">{progress}% complete</div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Your first 10 minutes</h2>
            <div className="mt-4 space-y-3">
              {steps.map((step) => (
                <div key={step.id} className={`rounded-xl border p-3 ${screen === step.id || (screen === "results" && step.id === "results") ? "border-stone-900 bg-stone-900 text-white" : "border-stone-200 bg-stone-50 text-stone-700"}`}>
                  <div className="flex items-center gap-2">
                    {screen === step.id || (screen === "results" && step.id === "results") ? <CheckCircle2 className="h-4 w-4" /> : <CircleDashed className="h-4 w-4" />}
                    <p className="font-medium">{step.title}</p>
                  </div>
                  <p className={`mt-1 text-sm ${screen === step.id || (screen === "results" && step.id === "results") ? "text-stone-300" : "text-stone-600"}`}>{step.detail}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            {screen === "welcome" && (
              <div className="space-y-5">
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-semibold">Why Synzept feels different</p>
                  <p className="mt-2 text-sm text-stone-600">Within minutes, Synzept turns your priorities into a mission, a Daily OS, an Action Center, and an initial knowledge graph preview.</p>
                </div>
                <div className="space-y-3">
                  <div className="flex items-start gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-stone-600">
                    <Compass className="mt-0.5 h-4 w-4" />
                    <span>It builds an initial understanding of who you are and what matters.</span>
                  </div>
                  <div className="flex items-start gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-stone-600">
                    <Sparkles className="mt-0.5 h-4 w-4" />
                    <span>It creates your first mission and highest-impact next action immediately.</span>
                  </div>
                </div>
                <button onClick={handleContinue} className="flex items-center gap-2 rounded-full bg-stone-900 px-4 py-2 text-sm font-medium text-white">Start the experience <ArrowRight className="h-4 w-4" /></button>
              </div>
            )}

            {screen === "interview" && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Smart onboarding interview</p>
                  <h2 className="mt-1 text-2xl font-semibold">We only need a tiny bit of context</h2>
                </div>
                <label className="block text-sm font-medium text-stone-700">
                  What do you want to make progress on today?
                  <input value={focusArea} onChange={(event) => setFocusArea(event.target.value)} placeholder="Launch readiness, clarity, or focus" className="mt-2 w-full rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm outline-none" />
                </label>
                <label className="block text-sm font-medium text-stone-700">
                  What is your main goal right now?
                  <input value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="Ship the beta, find focus, or reduce noise" className="mt-2 w-full rounded-xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm outline-none" />
                </label>
                <button onClick={handleContinue} className="flex items-center gap-2 rounded-full bg-stone-900 px-4 py-2 text-sm font-medium text-white">Continue <ArrowRight className="h-4 w-4" /></button>
              </div>
            )}

            {screen === "reasoning" && (
              <div className="space-y-4">
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-semibold">AI reasoning</p>
                  <p className="mt-2 text-sm text-stone-600">Synzept is connecting your context to a mission, Daily OS, Action Center, and life graph preview.</p>
                </div>
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4 text-sm text-stone-600">
                  We are generating your first insights, your next best action, and a personalized starting point.
                </div>
              </div>
            )}

            {screen === "results" && (
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">First wow moment</p>
                  <h2 className="mt-1 text-2xl font-semibold">You already have a clear starting point</h2>
                </div>
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-semibold">Mission</p>
                  <p className="mt-2 text-sm text-stone-600">Build a calm operating system for your next big move.</p>
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <p className="text-sm font-semibold">Daily OS</p>
                    <p className="mt-2 text-sm text-stone-600">Protect one deep work block and one review ritual each day.</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <p className="text-sm font-semibold">Action Center</p>
                    <p className="mt-2 text-sm text-stone-600">Review your next milestone, decline low-value scope, capture one insight before the day ends.</p>
                  </div>
                </div>
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-semibold">Three meaningful insights</p>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-stone-600">
                    <li>You move faster when you define milestones early.</li>
                    <li>Your best decisions follow evidence and reflection.</li>
                    <li>Scope control protects momentum more than extra features.</li>
                  </ul>
                </div>
                <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-semibold">Highest-impact next action</p>
                  <p className="mt-2 text-sm text-stone-600">Schedule a 20-minute review and lock your first milestone.</p>
                </div>
                <button onClick={() => setCompleted(true)} className="flex items-center gap-2 rounded-full bg-stone-900 px-4 py-2 text-sm font-medium text-white">Enter Synzept <ChevronRight className="h-4 w-4" /></button>
              </div>
            )}

            {completed && (
              <div className="space-y-4">
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-emerald-800">
                  <p className="text-sm font-semibold">You’ve completed the wow experience</p>
                  <p className="mt-2 text-sm">Synzept now has a strong first understanding of your direction and your next best move.</p>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

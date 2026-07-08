"use client";

import { CheckCircle2, Clock3, Compass, Sparkles, Target, Zap } from "lucide-react";

const dashboard = {
  missionTitle: "Launch Synzept V2",
  progress: 72,
  currentMilestone: "Polish onboarding and activate the first daily workflow",
  actions: [
    { id: "action-1", title: "Simplify the workspace setup", estimatedTime: "15 min", priority: "High", reason: "Biggest activation blocker today." },
    { id: "action-2", title: "Ship the Daily Brief prompt", estimatedTime: "25 min", priority: "High", reason: "Creates immediate value for returning users." },
    { id: "action-3", title: "Capture one onboarding insight", estimatedTime: "10 min", priority: "Medium", reason: "A single insight can guide the next iteration." },
  ],
  avoidList: ["Rebuilding the full onboarding flow today", "Adding new experimental features before the core loop is clear"],
  aiInsight: "Progress is slowing because one setup step is creating friction for first-time users.",
  momentumScore: 84,
  weeklyTrend: "Upward",
  streak: 5,
  motivationMessage: "You are building momentum. Keep the next step small and clear.",
  openLoops: ["Clarify the first-run value proposition", "Decide how search should appear in the early workflow", "Follow up on the first onboarding interviews"],
  quickActions: ["Start Focus Session", "Capture Thought", "Ask Synzept", "Review Yesterday"],
};

export default function ActionCenterPage() {
  return (
    <main className="min-h-screen bg-stone-50 p-4 text-stone-900 sm:p-6">
      <div className="mx-auto flex max-w-6xl flex-col gap-4">
        <header className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-7">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Action Center</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">What should I do next?</h1>
            </div>
            <div className="rounded-2xl bg-stone-900 p-3 text-white">
              <Compass className="h-5 w-5" />
            </div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center gap-2 text-stone-700">
              <Target className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Today&apos;s Mission</h2>
            </div>
            <h3 className="mt-4 text-2xl font-semibold">{dashboard.missionTitle}</h3>
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-100">
              <div className="h-full rounded-full bg-stone-900" style={{ width: `${dashboard.progress}%` }} />
            </div>
            <p className="mt-3 text-sm leading-6 text-stone-600">{dashboard.currentMilestone}</p>
            <p className="mt-2 text-sm font-medium text-stone-500">Progress {dashboard.progress}%</p>
          </div>

          <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center gap-2 text-stone-700">
              <Zap className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Momentum</h2>
            </div>
            <div className="mt-4 space-y-3 text-sm text-stone-600">
              <div className="rounded-2xl bg-stone-50 p-3"><span className="font-medium text-stone-900">Score:</span> {dashboard.momentumScore}</div>
              <div className="rounded-2xl bg-stone-50 p-3"><span className="font-medium text-stone-900">Trend:</span> {dashboard.weeklyTrend}</div>
              <div className="rounded-2xl bg-stone-50 p-3"><span className="font-medium text-stone-900">Streak:</span> {dashboard.streak} days</div>
              <div className="rounded-2xl bg-stone-50 p-3"><span className="font-medium text-stone-900">Motivation:</span> {dashboard.motivationMessage}</div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
            <div className="flex items-center gap-2 text-stone-700">
              <CheckCircle2 className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Top 3 Actions</h2>
            </div>
            <div className="mt-4 space-y-3">
              {dashboard.actions.map((action) => (
                <div key={action.id} className="flex items-start justify-between gap-3 rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <div>
                    <p className="font-medium text-stone-900">{action.title}</p>
                    <p className="mt-1 text-sm text-stone-600">{action.reason}</p>
                  </div>
                  <div className="text-right text-sm text-stone-500">
                    <p>{action.estimatedTime}</p>
                    <p className="mt-1 font-medium text-stone-700">{action.priority}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex items-center gap-2 text-stone-700">
                <Clock3 className="h-5 w-5" />
                <h2 className="text-xl font-semibold">Avoid List</h2>
              </div>
              <ul className="mt-4 space-y-2 text-sm leading-6 text-stone-600">
                {dashboard.avoidList.map((item) => <li key={item} className="rounded-2xl bg-stone-50 p-3">{item}</li>)}
              </ul>
            </div>

            <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
              <div className="flex items-center gap-2 text-stone-700">
                <Sparkles className="h-5 w-5" />
                <h2 className="text-xl font-semibold">AI Insight</h2>
              </div>
              <p className="mt-4 text-sm leading-6 text-stone-600">{dashboard.aiInsight}</p>
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-xl font-semibold">Open Loops</h2>
            <ul className="mt-4 space-y-2 text-sm leading-6 text-stone-600">
              {dashboard.openLoops.map((loop) => <li key={loop} className="rounded-2xl bg-stone-50 p-3">{loop}</li>)}
            </ul>
          </div>

          <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-xl font-semibold">Quick Actions</h2>
            <div className="mt-4 grid gap-2">
              {dashboard.quickActions.map((action) => (
                <button key={action} className="rounded-2xl border border-stone-200 bg-stone-50 px-3 py-3 text-left text-sm font-medium text-stone-700 transition hover:bg-stone-100">
                  {action}
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

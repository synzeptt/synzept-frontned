"use client";

import { CheckCircle2, Clock3, Sparkles, XCircle } from "lucide-react";

const opportunities = [
  {
    title: "Double down on onboarding clarity",
    summary: "Lower setup friction to improve activation and reduce early drop-off.",
    outcome: "Higher activation and stronger first-week value.",
    action: "Simplify the workspace setup screen and remove one optional decision.",
    score: 94,
  },
  {
    title: "Turn daily habits into momentum",
    summary: "A short review loop could make the product feel indispensable.",
    outcome: "More consistent engagement and better retention.",
    action: "Surface a one-minute daily review prompt after the first successful session.",
    score: 87,
  },
  {
    title: "Surface the most useful memories earlier",
    summary: "Make the memory layer more discoverable in the flow.",
    outcome: "Faster context recovery and better trust in the system.",
    action: "Prompt users with a memory reminder when they revisit a project they touched last week.",
    score: 76,
  },
];

export default function OpportunitiesPage() {
  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-stone-900 p-2 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Opportunities</p>
              <h1 className="text-3xl font-semibold">The highest-leverage next moves for Synzept</h1>
            </div>
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-stone-600">
            This section surfaces opportunities based on product context, current momentum, and likely leverage rather than just open tasks.
          </p>
        </header>

        <section className="grid gap-4">
          {opportunities.map((item, index) => (
            <article key={item.title} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-stone-900 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white">
                      #{index + 1}
                    </span>
                    <span className="text-sm text-stone-500">Opportunity score: {item.score}</span>
                  </div>
                  <h2 className="mt-3 text-xl font-semibold">{item.title}</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">{item.summary}</p>
                </div>
                <div className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm">
                  <p className="font-medium">Why it matters</p>
                  <p className="mt-2 text-stone-600">{item.outcome}</p>
                </div>
              </div>

              <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_auto]">
                <div className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-medium">Suggested first action</p>
                  <p className="mt-2 text-sm leading-6 text-stone-600">{item.action}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                    <CheckCircle2 className="h-4 w-4" />
                    Accept
                  </button>
                  <button className="flex items-center gap-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                    <Clock3 className="h-4 w-4" />
                    Snooze
                  </button>
                  <button className="flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                    <XCircle className="h-4 w-4" />
                    Dismiss
                  </button>
                </div>
              </div>
            </article>
          ))}
        </section>
      </div>
    </main>
  );
}

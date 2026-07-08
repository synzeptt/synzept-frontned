"use client";

import { Brain, Sparkles, TrendingUp } from "lucide-react";

const model = {
  userName: "Maya",
  summary: "Maya is a product-focused builder who values calm execution, strong context, and steady momentum.",
  domains: [
    {
      key: "identity",
      title: "Identity",
      attributes: [
        { value: "Founder-led product builder", confidence: 92 },
        { value: "Values clarity and calm systems", confidence: 88 },
      ],
    },
    {
      key: "goals",
      title: "Goals",
      attributes: [
        { value: "Increase activation in the first week", confidence: 90 },
        { value: "Create a repeatable daily operating rhythm", confidence: 86 },
      ],
    },
    {
      key: "work-style",
      title: "Work Style",
      attributes: [
        { value: "Prefers focused work in the morning", confidence: 81 },
        { value: "Likes short, concrete plans", confidence: 87 },
      ],
    },
    {
      key: "strengths",
      title: "Strengths",
      attributes: [
        { value: "Strong at turning context into action", confidence: 90 },
        { value: "Good at spotting activation problems", confidence: 86 },
      ],
    },
    {
      key: "growth-areas",
      title: "Growth Areas",
      attributes: [
        { value: "Needs better early discoverability for memory and search", confidence: 82 },
        { value: "Should reduce setup overhead", confidence: 88 },
      ],
    },
  ],
  learningTimeline: [
    "2026-07-01: Synzept inferred a preference for calm, focused workflows.",
    "2026-07-03: Confidence increased around onboarding and activation.",
    "2026-07-06: The model strengthened around daily ritual and momentum-based planning.",
  ],
};

export default function MyModelPage() {
  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-stone-900 p-2 text-white">
              <Brain className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">My Model</p>
              <h1 className="text-3xl font-semibold">Your personal knowledge model</h1>
            </div>
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-stone-600">{model.summary}</p>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {model.domains.map((domain) => (
            <div key={domain.key} className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-stone-700" />
                <h2 className="text-lg font-semibold">{domain.title}</h2>
              </div>
              <div className="mt-4 space-y-3">
                {domain.attributes.map((attribute) => (
                  <div key={`${domain.key}-${attribute.value}`} className="rounded-xl border border-stone-200 bg-stone-50 p-3">
                    <p className="text-sm font-medium text-stone-900">{attribute.value}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.2em] text-stone-500">Confidence {attribute.confidence}%</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </section>

        <section className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-stone-700" />
            <h2 className="text-xl font-semibold">Learning Timeline</h2>
          </div>
          <div className="mt-4 space-y-3">
            {model.learningTimeline.map((item) => (
              <div key={item} className="rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-stone-700">{item}</div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

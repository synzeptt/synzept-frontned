"use client";

import { useMemo, useState } from "react";
import { Search, Sparkles, Filter, ArrowRightLeft } from "lucide-react";

const journey = [
  {
    id: "tm-1",
    title: "Started the Synzept prototype",
    date: "2024-01-12",
    kind: "Mission",
    summary: "The first internal mission centered on proving that personal context could accelerate action quality.",
    tags: ["vision", "prototype"],
  },
  {
    id: "tm-2",
    title: "Chose a reflective, AI-first product direction",
    date: "2024-03-08",
    kind: "Decision",
    summary: "A decisive shift toward memory-driven workflows shaped the roadmap for the next six months.",
    tags: ["strategy", "product"],
  },
  {
    id: "tm-3",
    title: "Beta launch preparation",
    date: "2024-06-29",
    kind: "Project",
    summary: "Planning milestones early helped the team reduce launch uncertainty and improve delivery rhythm.",
    tags: ["launch", "delivery"],
  },
  {
    id: "tm-4",
    title: "Customer feedback clarified the core value",
    date: "2024-07-18",
    kind: "Conversation",
    summary: "User feedback made it clear that context and reflection were more important than raw automation.",
    tags: ["feedback", "value"],
  },
];

const turningPoints = [
  {
    title: "First paying customer",
    date: "2024-05-21",
    impact: "Created a stronger feedback loop and a sharper sense of urgency.",
  },
  {
    title: "Beta launch",
    date: "2024-08-03",
    impact: "Turned a private hypothesis into a public learning system.",
  },
];

const reflections = [
  {
    insight: "You make your best decisions after gathering customer feedback.",
    evidence: ["Customer feedback clarified the core value", "Beta launch preparation"],
  },
  {
    insight: "You complete projects faster when you define milestones early.",
    evidence: ["Beta launch preparation", "Started the Synzept prototype"],
  },
];

export default function TimeMachinePage() {
  const [query, setQuery] = useState("");
  const [view, setView] = useState<"journey" | "compare">("journey");

  const filteredJourney = useMemo(() => {
    if (!query.trim()) return journey;
    const q = query.toLowerCase();
    return journey.filter((entry) => [entry.title, entry.summary, ...entry.tags].join(" ").toLowerCase().includes(q));
  }, [query]);

  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-stone-900 p-2 text-white">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Time Machine</p>
                <h1 className="text-3xl font-semibold">Explore your history, turning points, and growth</h1>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-2xl border border-stone-200 bg-stone-50 px-3 py-2">
              <Search className="h-4 w-4 text-stone-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search through time"
                className="w-64 bg-transparent text-sm outline-none"
              />
            </div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Journey view</h2>
              <button
                onClick={() => setView(view === "journey" ? "compare" : "journey")}
                className="flex items-center gap-2 rounded-full border border-stone-200 bg-stone-50 px-3 py-1.5 text-sm text-stone-600"
              >
                <ArrowRightLeft className="h-4 w-4" />
                {view === "journey" ? "Compare mode" : "Journey mode"}
              </button>
            </div>

            <div className="mt-4 flex items-center gap-2 text-sm text-stone-500">
              <Filter className="h-4 w-4" />
              <span>Milestones • Projects • Goals • Memories • Conversations • Decisions • Habits</span>
            </div>

            <div className="mt-6 space-y-3">
              {filteredJourney.map((entry) => (
                <div key={entry.id} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{entry.title}</p>
                      <p className="mt-1 text-sm text-stone-600">{entry.summary}</p>
                    </div>
                    <div className="text-right text-xs uppercase tracking-[0.2em] text-stone-500">
                      <div>{entry.date}</div>
                      <div className="mt-1">{entry.kind}</div>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {entry.tags.map((tag) => (
                      <span key={tag} className="rounded-full border border-stone-200 bg-white px-2.5 py-1 text-xs text-stone-600">{tag}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold">Turning points</h2>
              <div className="mt-4 space-y-3">
                {turningPoints.map((point) => (
                  <div key={point.title} className="rounded-xl border border-amber-200 bg-amber-50 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-medium">{point.title}</p>
                      <span className="text-xs uppercase tracking-[0.2em] text-amber-700">{point.date}</span>
                    </div>
                    <p className="mt-2 text-sm text-stone-600">{point.impact}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold">Reflection engine</h2>
              <div className="mt-4 space-y-3">
                {reflections.map((reflection) => (
                  <div key={reflection.insight} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                    <p className="font-medium">{reflection.insight}</p>
                    <p className="mt-2 text-sm text-stone-600">Evidence: {reflection.evidence.join(" • ")}</p>
                  </div>
                ))}
              </div>
            </div>

            {view === "compare" ? (
              <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                <h2 className="text-xl font-semibold">Compare views</h2>
                <div className="mt-4 space-y-3">
                  <div className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                    <p className="font-medium">This month vs last month</p>
                    <p className="mt-2 text-sm text-stone-600">Before: More unstructured exploration and less emphasis on reflection.</p>
                    <p className="mt-1 text-sm text-stone-600">After: A clearer rhythm of review, stronger priorities, and better follow-through.</p>
                  </div>
                  <div className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                    <p className="font-medium">Before vs after the beta launch</p>
                    <p className="mt-2 text-sm text-stone-600">Before: Roadmap thinking was more abstract and less grounded in behavior.</p>
                    <p className="mt-1 text-sm text-stone-600">After: The product experience became more evidence-driven and user-informed.</p>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}

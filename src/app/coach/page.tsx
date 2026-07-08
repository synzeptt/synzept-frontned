"use client";

import { useMemo, useState } from "react";
import { Sparkles, BellOff, MoonStar, SunMedium, CalendarDays } from "lucide-react";

const sections = [
  {
    id: "morning",
    title: "Morning Brief",
    focus: "Launch readiness",
    summary: "You have momentum on the beta launch and a strong weekly review rhythm.",
    evidence: [
      "Two milestones were completed this week",
      "The weekly review habit is now consistent",
      "A customer insight pointed to a clearer product message",
    ],
    action: "Protect the next 90 minutes for milestone review and stakeholder alignment.",
  },
  {
    id: "midday",
    title: "Midday Check-in",
    focus: "Stay aligned",
    summary: "The day is progressing well. The main risk is drifting into low-priority scope.",
    evidence: [
      "Your current project board has three high-priority items",
      "One task is still waiting on approval",
      "A new request could expand scope unexpectedly",
    ],
    action: "Decline the extra scope request and keep the roadmap focused.",
  },
  {
    id: "evening",
    title: "Evening Reflection",
    focus: "Review what mattered",
    summary: "You made progress by protecting focus and closing the loop on customer feedback.",
    evidence: [
      "The launch plan is clearer than yesterday",
      "Your review ritual reduced overthinking",
      "You left the day with a stronger sense of momentum",
    ],
    action: "Tomorrow, start with the highest-leverage milestone and avoid inbox-driven work first.",
  },
  {
    id: "weekly",
    title: "Weekly Coaching Summary",
    focus: "Momentum and course correction",
    summary: "This week showed steady progress with one important lesson: scope control matters.",
    evidence: [
      "Milestones were clearer this week",
      "The week ended with stronger follow-through",
      "The biggest drag came from new requests",
    ],
    action: "Keep the weekly review ritual and protect one deep work block each day.",
  },
];

export default function CoachPage() {
  const [selectedId, setSelectedId] = useState("morning");
  const selectedSection = useMemo(() => sections.find((section) => section.id === selectedId) ?? sections[0], [selectedId]);

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
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Synzept Coach</p>
                <h1 className="text-3xl font-semibold">Quiet, evidence-based guidance for your day</h1>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-2xl border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-600">
              <BellOff className="h-4 w-4" />
              Snooze or disable coaching anytime
            </div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">Coach moments</h2>
              <div className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-sm text-stone-600">Low volume</div>
            </div>
            <div className="mt-4 space-y-3">
              {sections.map((section) => (
                <button
                  key={section.id}
                  onClick={() => setSelectedId(section.id)}
                  className={`w-full rounded-xl border p-4 text-left transition ${selectedId === section.id ? "border-stone-900 bg-stone-900 text-white" : "border-stone-200 bg-stone-50 text-stone-700"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{section.title}</p>
                      <p className={`mt-1 text-sm ${selectedId === section.id ? "text-stone-200" : "text-stone-600"}`}>{section.focus}</p>
                    </div>
                    <CalendarDays className="h-4 w-4" />
                  </div>
                </button>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Selected moment</p>
                <h2 className="mt-1 text-2xl font-semibold">{selectedSection.title}</h2>
              </div>
              <div className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-sm text-stone-600">Evidence-based</div>
            </div>

            <div className="mt-6 rounded-2xl border border-stone-200 bg-stone-50 p-5">
              <div className="flex items-center gap-2 text-stone-700">
                {selectedSection.id === "morning" ? <SunMedium className="h-4 w-4" /> : selectedSection.id === "evening" ? <MoonStar className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
                <p className="text-sm font-semibold">{selectedSection.summary}</p>
              </div>
              <div className="mt-4 rounded-2xl border border-stone-200 bg-white p-4">
                <p className="text-sm font-semibold">Recommended action</p>
                <p className="mt-2 text-sm text-stone-600">{selectedSection.action}</p>
              </div>
            </div>

            <div className="mt-6">
              <p className="text-sm font-semibold">Using your own evidence</p>
              <div className="mt-3 space-y-2">
                {selectedSection.evidence.map((item) => (
                  <div key={item} className="rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-stone-600">{item}</div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

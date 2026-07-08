"use client";

import { useMemo, useState } from "react";
import { Search, Sparkles, AlertTriangle, CheckCircle2, MessageSquareQuote } from "lucide-react";

const recommendations = [
  {
    id: "trust-1",
    recommendation: "Prioritize a milestone-first launch plan for the next beta cycle.",
    why: "Your strongest decisions tended to come from evidence and early milestones, not broad scope expansion.",
    confidenceScore: 0.91,
    confidenceLevel: "High",
    confidenceExplanation: "The recommendation is grounded in repeated patterns and multiple supporting events.",
    supportingEvidence: [
      { title: "Captured the lessons from the first major setback", detail: "This memory highlights that delays often came from scope expansion." },
      { title: "Beta launch preparation", detail: "Milestones early in the project lined up with a calmer launch rhythm." },
    ],
    relatedMemories: ["Lessons from the first major setback"],
    relatedMissions: ["Synzept prototype"],
    relatedDecisions: ["Reflective AI-first direction"],
    relatedConversations: ["Feedback from early adopters"],
    alternativeOptions: ["Ship more features without milestones", "Delay the launch until everything is perfect"],
    risks: ["Reducing scope could leave some requested features unaddressed"],
    expectedOutcome: "Faster execution with lower launch risk and clearer team focus.",
    assumptions: ["The next beta cycle still values clarity over feature volume"],
    missingInformation: [],
  },
  {
    id: "trust-2",
    recommendation: "Create a lightweight review ritual before major decisions.",
    why: "Your best decisions followed a period of reflection and evidence gathering.",
    confidenceScore: 0.72,
    confidenceLevel: "Medium",
    confidenceExplanation: "The pattern is strong, but the recommendation depends on how much context you want reviewed before acting.",
    supportingEvidence: [
      { title: "Customer feedback clarified the core value", detail: "The review pointed to more reflective planning and less reactive expansion." },
    ],
    relatedMemories: ["Weekly review habit"],
    relatedMissions: ["Reflection loop"],
    relatedDecisions: ["Weekly review habit formed"],
    relatedConversations: ["Early customer interviews"],
    alternativeOptions: ["Skip the review and move fast", "Use a longer retrospective instead"],
    risks: ["The ritual might feel overly formal"],
    expectedOutcome: "Improved clarity before important choices and more consistent follow-through.",
    assumptions: ["You want a short review ritual rather than a full retrospective"],
    missingInformation: ["I do not know how much time you have before major decisions."],
  },
];

export default function TrustEnginePage() {
  const [query, setQuery] = useState("");
  const filteredRecommendations = useMemo(() => {
    if (!query.trim()) return recommendations;
    const q = query.toLowerCase();
    return recommendations.filter((item) => [item.recommendation, item.why, item.confidenceExplanation].join(" ").toLowerCase().includes(q));
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
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Trust Engine</p>
                <h1 className="text-3xl font-semibold">Transparent, explainable, and reviewable recommendations</h1>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-2xl border border-stone-200 bg-stone-50 px-3 py-2">
              <Search className="h-4 w-4 text-stone-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Find a recommendation"
                className="w-64 bg-transparent text-sm outline-none"
              />
            </div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-4">
            {filteredRecommendations.map((item) => (
              <article key={item.id} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Recommendation</p>
                    <h2 className="mt-1 text-xl font-semibold">{item.recommendation}</h2>
                  </div>
                  <div className={`rounded-full px-3 py-1 text-sm font-medium ${item.confidenceLevel === "High" ? "bg-emerald-50 text-emerald-700" : item.confidenceLevel === "Medium" ? "bg-amber-50 text-amber-700" : "bg-rose-50 text-rose-700"}`}>
                    {item.confidenceLevel} • {Math.round(item.confidenceScore * 100)}%
                  </div>
                </div>

                <div className="mt-4 rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-semibold">Why this recommendation</p>
                  <p className="mt-2 text-sm text-stone-600">{item.why}</p>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-semibold">Based on</p>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-stone-600">
                      {item.basedOn.map((entry) => <li key={entry}>{entry}</li>)}
                    </ul>
                  </div>
                  <div>
                    <p className="text-sm font-semibold">Confidence</p>
                    <p className="mt-2 text-sm text-stone-600">{item.confidenceExplanation}</p>
                  </div>
                </div>

                <div className="mt-4 rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-sm font-semibold">Evidence panel</p>
                  <div className="mt-3 space-y-2">
                    {item.supportingEvidence.map((evidence) => (
                      <div key={evidence.title} className="rounded-xl border border-stone-200 bg-white p-3">
                        <p className="text-sm font-medium">{evidence.title}</p>
                        <p className="mt-1 text-sm text-stone-600">{evidence.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <p className="text-sm font-semibold">Related context</p>
                    <p className="mt-2 text-sm text-stone-600">Memories: {item.relatedMemories.join(", ")}</p>
                    <p className="mt-1 text-sm text-stone-600">Missions: {item.relatedMissions.join(", ")}</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <p className="text-sm font-semibold">Alternatives & risks</p>
                    <p className="mt-2 text-sm text-stone-600">Alternatives: {item.alternativeOptions.join(" • ")}</p>
                    <p className="mt-1 text-sm text-stone-600">Risks: {item.risks.join(" • ")}</p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                  <span className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-xs uppercase tracking-[0.2em] text-stone-500">Expected outcome: {item.expectedOutcome}</span>
                </div>

                <div className="mt-4 border-t border-stone-200 pt-4">
                  <div className="flex flex-wrap gap-3">
                    <button className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-medium text-emerald-700">
                      <CheckCircle2 className="h-4 w-4" /> Helpful
                    </button>
                    <button className="flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-sm font-medium text-amber-700">
                      <AlertTriangle className="h-4 w-4" /> Needs more context
                    </button>
                    <button className="flex items-center gap-2 rounded-full border border-stone-200 bg-stone-50 px-3 py-1.5 text-sm font-medium text-stone-700">
                      <MessageSquareQuote className="h-4 w-4" /> Feedback
                    </button>
                  </div>
                </div>
              </article>
            ))}
          </div>

          <aside className="space-y-4">
            <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold">Missing information</h2>
              <div className="mt-4 space-y-3">
                {recommendations.flatMap((item) => item.missingInformation).length === 0 ? (
                  <p className="text-sm text-stone-600">No missing information flagged for the current mock recommendations.</p>
                ) : (
                  recommendations.flatMap((item) => item.missingInformation).map((entry) => (
                    <div key={entry} className="rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-stone-600">{entry}</div>
                  ))
                )}
              </div>
            </div>
            <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
              <h2 className="text-xl font-semibold">Assumptions</h2>
              <div className="mt-4 space-y-2">
                {recommendations.flatMap((item) => item.assumptions).map((entry) => (
                  <div key={entry} className="rounded-xl border border-stone-200 bg-stone-50 p-3 text-sm text-stone-600">{entry}</div>
                ))}
              </div>
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}

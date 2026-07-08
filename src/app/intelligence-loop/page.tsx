"use client";

import { Brain, CheckCircle2, Eye, Lightbulb, ShieldCheck, Sparkles, Target, TrendingUp } from "lucide-react";

const snapshot = {
  generatedAt: "2026-07-07T09:45:00+05:30",
  loopHealth: {
    status: "mock_ready",
    observedEvents: 7,
    predictions: 4,
    recommendations: 3,
    pendingApprovals: 3,
    learningOutcomes: 2,
  },
  stages: [
    { label: "Observe", icon: Eye, count: 7, text: "Normalized events from conversations, missions, projects, tasks, notes, decisions, and memories." },
    { label: "Understand", icon: Brain, count: 5, text: "Evolving user model for goals, priorities, interests, relationships, and working patterns." },
    { label: "Predict", icon: TrendingUp, count: 4, text: "Forward-looking risks, probabilities, blockers, and opportunities with evidence." },
    { label: "Recommend", icon: Lightbulb, count: 3, text: "Ranked actions by expected impact, confidence, and current priorities." },
    { label: "Act", icon: ShieldCheck, count: 3, text: "Permission-based action requests that wait for explicit approval." },
    { label: "Learn", icon: CheckCircle2, count: 2, text: "Accepted, ignored, rejected, successful, and unsuccessful outcomes adjust future ranking." },
  ],
  userModel: [
    { label: "Launch Synzept V2", category: "Goal", confidence: 0.67, evidence: "Memory Feed and V2 mission progress" },
    { label: "Integrate intelligence surfaces", category: "Priority", confidence: 0.71, evidence: "Multiple V2 engines now need one loop contract" },
    { label: "Close beta follow-ups", category: "Priority", confidence: 0.57, evidence: "External commitment and deadline signals" },
    { label: "Continuity and proactive recall", category: "Interest", confidence: 0.64, evidence: "Recurring product principle across notes" },
    { label: "Small implementation increments", category: "Pattern", confidence: 0.56, evidence: "Recent accepted actions were 15 to 30 minutes" },
  ],
  predictions: [
    { title: "V2 foundation likely to reach usable prototype this week", probability: 74, confidence: 67, risk: "Medium", evidence: "Core surfaces exist; integration is the remaining leverage point." },
    { title: "Beta invite follow-up has elevated miss risk", probability: 68, confidence: 81, risk: "High", evidence: "External, time-sensitive, and competing with platform implementation." },
    { title: "Feature fragmentation may slow V2 clarity", probability: 72, confidence: 78, risk: "Medium", evidence: "Several useful surfaces need one shared loop contract." },
    { title: "Daily recall can become the retention ritual", probability: 79, confidence: 76, risk: "Low", evidence: "A ranked first screen creates immediate return value." },
  ],
  recommendations: [
    { title: "Make every V2 surface emit Intelligence Loop events", score: 84.3, impact: 94, effort: "45 min", why: "This gives Synzept one shared learning substrate." },
    { title: "Send the private beta invite before adding new surface work", score: 82.9, impact: 88, effort: "15 min", why: "The commitment involves people waiting on you." },
    { title: "Use Memory Feed as the first consumer of predictions", score: 78.4, impact: 86, effort: "30 min", why: "The feed already answers what changed and what needs attention." },
  ],
  approvals: [
    { title: "Approve: Use the common event model", status: "pending approval", preview: "No production action is executed in mock mode." },
    { title: "Approve: Draft a private beta invite", status: "pending approval", preview: "Synzept asks before contacting anyone." },
    { title: "Approve: Add predictions to Memory Feed", status: "pending approval", preview: "Creates a mock implementation task only." },
  ],
  learning: [
    { outcome: "Accepted", adjustment: "Increase weight for external commitments with near-term deadlines." },
    { outcome: "Rejected", adjustment: "Reduce priority for new surfaces before integration work is complete." },
  ],
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function IntelligenceLoopPage() {
  return (
    <main className="min-h-screen bg-stone-50 p-4 text-stone-950 sm:p-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="rounded-lg border border-border bg-white p-5 shadow-soft sm:p-6">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Synzept Intelligence Loop</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">Observe, understand, predict, recommend, act, learn</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
                The shared AI platform layer behind every product surface. This mock console shows the loop contract before production data is connected.
              </p>
            </div>
            <div className="rounded-md border border-border bg-surface px-3 py-2 text-sm text-muted-foreground">
              Generated {formatDate(snapshot.generatedAt)}
            </div>
          </div>
        </header>

        <section className="grid gap-3 md:grid-cols-3 xl:grid-cols-6">
          {snapshot.stages.map((stage) => (
            <article key={stage.label} className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <div className="flex items-center justify-between gap-3">
                <stage.icon className="h-5 w-5 text-stone-700" />
                <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-700">{stage.count}</span>
              </div>
              <h2 className="mt-4 text-base font-semibold">{stage.label}</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{stage.text}</p>
            </article>
          ))}
        </section>

        <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <div className="flex items-center gap-2">
              <Target className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Evolving User Model</h2>
            </div>
            <div className="mt-4 space-y-3">
              {snapshot.userModel.map((signal) => (
                <div key={signal.label} className="rounded-md border border-border bg-surface p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold">{signal.label}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{signal.category} / {signal.evidence}</p>
                    </div>
                    <span className="text-sm font-semibold">{Math.round(signal.confidence * 100)}%</span>
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-stone-200">
                    <div className="h-full rounded-full bg-stone-900" style={{ width: `${signal.confidence * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Predictions</h2>
            </div>
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {snapshot.predictions.map((prediction) => (
                <article key={prediction.title} className="rounded-md border border-border bg-surface p-4">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-sm font-semibold leading-5">{prediction.title}</h3>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs font-medium text-stone-700">{prediction.risk}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{prediction.evidence}</p>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-md bg-white p-2"><span className="text-muted-foreground">Probability</span><p className="mt-1 font-semibold">{prediction.probability}%</p></div>
                    <div className="rounded-md bg-white p-2"><span className="text-muted-foreground">Confidence</span><p className="mt-1 font-semibold">{prediction.confidence}%</p></div>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Ranked Recommendations</h2>
            </div>
            <div className="mt-4 space-y-3">
              {snapshot.recommendations.map((recommendation, index) => (
                <article key={recommendation.title} className="rounded-md border border-border bg-surface p-4">
                  <div className="flex items-start gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-900 text-sm font-semibold text-white">{index + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <h3 className="text-sm font-semibold">{recommendation.title}</h3>
                        <span className="text-sm font-semibold">{recommendation.score}</span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{recommendation.why}</p>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs text-stone-600">
                        <span className="rounded-full bg-white px-2.5 py-1">Impact {recommendation.impact}</span>
                        <span className="rounded-full bg-white px-2.5 py-1">{recommendation.effort}</span>
                        <span className="rounded-full bg-white px-2.5 py-1">Requires approval</span>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5" />
                <h2 className="text-xl font-semibold">Permissioned Actions</h2>
              </div>
              <div className="mt-4 space-y-3">
                {snapshot.approvals.map((approval) => (
                  <div key={approval.title} className="rounded-md border border-border bg-surface p-3">
                    <p className="text-sm font-semibold">{approval.title}</p>
                    <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">{approval.status}</p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{approval.preview}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                <h2 className="text-xl font-semibold">Learning Outcomes</h2>
              </div>
              <div className="mt-4 space-y-3">
                {snapshot.learning.map((item) => (
                  <div key={item.adjustment} className="rounded-md bg-surface p-3">
                    <p className="text-sm font-semibold">{item.outcome}</p>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.adjustment}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

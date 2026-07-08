import { PageFrame } from "@frontend/components/layout/page-frame";
import { DecisionShell } from "@/components/decision-intelligence/DecisionShell";
import { DecisionStat } from "@/components/decision-intelligence/DecisionPrimitives";
import { decisionIntelligenceMock } from "@/lib/decision-intelligence/mock-data";

export default function DecisionAnalyticsPage() {
  const { analytics, outcomeAnalyses } = decisionIntelligenceMock;

  return (
    <PageFrame eyebrow="Decision Intelligence" title="Decision Analytics">
      <DecisionShell active="Analytics">
        <section className="grid gap-3 md:grid-cols-5">
          <DecisionStat label="Total decisions" value={analytics.totalDecisions} />
          <DecisionStat label="Pending reviews" value={analytics.pendingReviews} />
          <DecisionStat label="Completed reviews" value={analytics.completedReviews} />
          <DecisionStat label="Avg accuracy" value={`${analytics.averagePredictionAccuracy}%`} />
          <DecisionStat label="Success rate" value={`${analytics.highConfidenceSuccessRate}%`} />
        </section>
        <section className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <h2 className="text-lg font-semibold">Recurring Risk Themes</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {analytics.recurringRiskThemes.map((theme) => <span key={theme} className="rounded-full bg-stone-100 px-2.5 py-1 text-sm text-stone-700">{theme}</span>)}
            </div>
          </div>
          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <h2 className="text-lg font-semibold">Outcome Analyses</h2>
            <div className="mt-4 space-y-3">
              {outcomeAnalyses.map((outcome) => (
                <article key={outcome.id} className="rounded-md bg-surface p-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold">{outcome.actualOutcome}</p>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs text-stone-700">{outcome.predictionAccuracy}%</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{outcome.lessonsLearned.join(" ")}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </DecisionShell>
    </PageFrame>
  );
}

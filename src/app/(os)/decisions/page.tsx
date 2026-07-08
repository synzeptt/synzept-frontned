import { PageFrame } from "@frontend/components/layout/page-frame";
import { DecisionShell } from "@/components/decision-intelligence/DecisionShell";
import { DecisionCard, DecisionStat, RecommendationCard } from "@/components/decision-intelligence/DecisionPrimitives";
import { decisionIntelligenceMock } from "@/lib/decision-intelligence/mock-data";

export default function DecisionFeedPage() {
  const { analytics, decisions, detectionCandidates, recommendations } = decisionIntelligenceMock;

  return (
    <PageFrame eyebrow="Decision Intelligence" title="Decision Feed">
      <DecisionShell active="Feed">
        <section className="grid gap-3 md:grid-cols-4">
          <DecisionStat label="Total decisions" value={analytics.totalDecisions} />
          <DecisionStat label="Pending reviews" value={analytics.pendingReviews} />
          <DecisionStat label="Prediction accuracy" value={`${analytics.averagePredictionAccuracy}%`} />
          <DecisionStat label="High-confidence success" value={`${analytics.highConfidenceSuccessRate}%`} />
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <main className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold">Decision Feed</h2>
              <p className="mt-1 text-sm text-muted-foreground">Meaningful choices captured with evidence, status, confidence, and review state.</p>
            </div>
            {decisions.map((decision) => <DecisionCard key={decision.id} decision={decision} />)}
          </main>

          <aside className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="text-lg font-semibold">Detection Suggestions</h2>
              <div className="mt-4 space-y-3">
                {detectionCandidates.map((candidate) => (
                  <article key={candidate.id} className="rounded-md bg-surface p-3">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-sm font-semibold">{candidate.suggestedTitle}</h3>
                      <span className="text-sm font-semibold">{Math.round(candidate.confidence * 100)}%</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{candidate.rationale}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="space-y-3">
              <h2 className="text-lg font-semibold">Future Recommendations</h2>
              {recommendations.map((recommendation) => <RecommendationCard key={recommendation.id} recommendation={recommendation} />)}
            </section>
          </aside>
        </section>
      </DecisionShell>
    </PageFrame>
  );
}

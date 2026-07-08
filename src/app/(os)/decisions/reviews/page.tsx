import { PageFrame } from "@frontend/components/layout/page-frame";
import { DecisionShell } from "@/components/decision-intelligence/DecisionShell";
import { decisionIntelligenceMock } from "@/lib/decision-intelligence/mock-data";

export default function DecisionReviewsPage() {
  return (
    <PageFrame eyebrow="Decision Intelligence" title="Decision Reviews">
      <DecisionShell active="Reviews">
        <section className="grid gap-4 lg:grid-cols-2">
          {decisionIntelligenceMock.reviews.map((review) => (
            <article key={review.id} className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex items-start justify-between gap-3">
                <h2 className="text-lg font-semibold">{review.decisionTitle}</h2>
                <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{review.reviewState}</span>
              </div>
              <p className="mt-3 text-sm font-medium text-stone-700">{review.prompt}</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{review.recommendedUpdate}</p>
              <div className="mt-4 rounded-md bg-surface px-3 py-2 text-sm text-stone-700">Scheduled {new Date(review.scheduledFor).toLocaleDateString()}</div>
            </article>
          ))}
        </section>
      </DecisionShell>
    </PageFrame>
  );
}

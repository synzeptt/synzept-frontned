import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { PageFrame } from "@frontend/components/layout/page-frame";
import { DecisionShell } from "@/components/decision-intelligence/DecisionShell";
import { DecisionStat } from "@/components/decision-intelligence/DecisionPrimitives";
import { decisionIntelligenceMock } from "@/lib/decision-intelligence/mock-data";

export default async function DecisionDetailsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const decision = decisionIntelligenceMock.decisions.find((item) => item.id === id);
  const outcome = decisionIntelligenceMock.outcomeAnalyses.find((item) => item.decisionId === id);
  if (!decision) notFound();

  return (
    <PageFrame eyebrow="Decision Intelligence" title="Decision Details">
      <DecisionShell active="Feed">
        <Link href="/decisions" className="inline-flex items-center gap-2 text-sm font-medium text-stone-700">
          <ArrowLeft className="h-4 w-4" />
          Decision Feed
        </Link>
        <article className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{decision.importance}</span>
                <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{decision.currentStatus}</span>
                <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{decision.reviewState}</span>
              </div>
              <h1 className="mt-3 text-3xl font-semibold tracking-normal">{decision.title}</h1>
              <p className="mt-3 max-w-4xl text-sm leading-6 text-muted-foreground">{decision.description}</p>
            </div>
            <DecisionStat label="Confidence" value={`${Math.round(decision.confidence * 100)}%`} />
          </div>
        </article>

        <section className="grid gap-5 lg:grid-cols-2">
          <InfoBlock title="Mission" items={[decision.mission]} />
          <InfoBlock title="Goal" items={[decision.goal]} />
          <InfoBlock title="Related Projects" items={decision.relatedProjects} />
          <InfoBlock title="Related People" items={decision.relatedPeople.length ? decision.relatedPeople : ["None recorded"]} />
          <InfoBlock title="Alternatives Considered" items={decision.alternativesConsidered} />
          <InfoBlock title="Risks" items={decision.risks} />
        </section>

        <section className="grid gap-5 lg:grid-cols-2">
          <InfoBlock title="Expected Outcome" items={[decision.expectedOutcome]} />
          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <h2 className="text-lg font-semibold">Evidence</h2>
            <div className="mt-3 space-y-3">
              {decision.evidence.map((item) => (
                <div key={item.id} className="rounded-md bg-surface p-3">
                  <p className="text-sm font-medium">{item.sourceTitle}</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{item.quote}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {outcome && (
          <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <h2 className="text-lg font-semibold">Outcome Analysis</h2>
            <div className="mt-4 grid gap-4 lg:grid-cols-3">
              <DecisionStat label="Prediction accuracy" value={`${outcome.predictionAccuracy}%`} />
              <InfoBlock title="Actual Outcome" items={[outcome.actualOutcome]} />
              <InfoBlock title="Lessons Learned" items={outcome.lessonsLearned} />
            </div>
          </section>
        )}
      </DecisionShell>
    </PageFrame>
  );
}

function InfoBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <h2 className="text-lg font-semibold">{title}</h2>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-stone-700">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

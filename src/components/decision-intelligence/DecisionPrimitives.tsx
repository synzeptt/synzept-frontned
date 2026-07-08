import Link from "next/link";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { DecisionDNATrait, DecisionRecord, DecisionRecommendation } from "@/lib/decision-intelligence/types";

export function DecisionStat({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return (
    <div className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-stone-950">{value}</p>
      {detail && <p className="mt-1 text-xs text-muted-foreground">{detail}</p>}
    </div>
  );
}

export function DecisionCard({ decision }: { decision: DecisionRecord }) {
  return (
    <Link href={`/decisions/${decision.id}`} className="block rounded-lg border border-border bg-white p-4 shadow-soft hover:bg-stone-50">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{decision.importance}</span>
            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{decision.currentStatus}</span>
            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{decision.reviewState}</span>
          </div>
          <h2 className="mt-3 text-lg font-semibold leading-6">{decision.title}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{decision.description}</p>
        </div>
        <div className="shrink-0 text-sm font-semibold text-stone-700">{Math.round(decision.confidence * 100)}%</div>
      </div>
      <div className="mt-4 flex items-center justify-between gap-3 text-sm text-stone-600">
        <span>{decision.mission}</span>
        <span className="inline-flex items-center gap-1 font-medium">Details <ArrowRight className="h-4 w-4" /></span>
      </div>
    </Link>
  );
}

export function DNATraitCard({ trait }: { trait: DecisionDNATrait }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{trait.category}</p>
            <h2 className="mt-1 text-lg font-semibold">{trait.title}</h2>
          </div>
          <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{Math.round(trait.confidence * 100)}%</span>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm leading-6 text-muted-foreground">{trait.summary}</p>
        <div className="mt-4 space-y-1.5">
          {trait.supportingEvidence.map((item) => (
            <p key={item} className="flex items-center gap-2 text-sm text-stone-700">
              <CheckCircle2 className="h-4 w-4 text-stone-500" />
              {item}
            </p>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function RecommendationCard({ recommendation }: { recommendation: DecisionRecommendation }) {
  return (
    <article className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-base font-semibold leading-6">{recommendation.title}</h2>
        <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">Impact {recommendation.expectedImpact}</span>
      </div>
      <p className="mt-3 text-sm font-medium text-stone-700">{recommendation.scenario}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{recommendation.recommendation}</p>
      <div className="mt-4 rounded-md bg-surface p-3">
        <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Reasoning</p>
        <p className="mt-1 text-sm leading-6 text-stone-700">{recommendation.reasoning}</p>
      </div>
    </article>
  );
}

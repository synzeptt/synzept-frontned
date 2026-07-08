"use client";

import { useState } from "react";
import { EyeOff, Globe2, LockKeyhole, Network, ShieldCheck, UsersRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { privacyIntelligenceMock } from "@/lib/privacy-intelligence/mock-data";

export function PrivacyIntelligenceView() {
  const [optedIn, setOptedIn] = useState(privacyIntelligenceMock.contributionSettings.optedIn);

  return (
    <div className="min-h-full bg-stone-50 text-stone-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-muted">
                <ShieldCheck className="h-4 w-4" />
                Privacy-Preserving Intelligence Network
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">Learn globally without exposing anyone personally</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
                Recommendations can use both your private context and anonymous community-level patterns, but the evidence is separated and labeled every time.
              </p>
            </div>
            <div className="rounded-lg border border-border bg-surface p-4 lg:w-80">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold">Anonymous contribution</p>
                  <p className="mt-1 text-xs text-muted-foreground">{optedIn ? "Opted in" : "Local only"}</p>
                </div>
                <button
                  type="button"
                  onClick={() => setOptedIn((value) => !value)}
                  className={`h-7 w-12 rounded-full p-1 transition ${optedIn ? "bg-stone-900" : "bg-stone-300"}`}
                  aria-pressed={optedIn}
                >
                  <span className={`block h-5 w-5 rounded-full bg-white transition ${optedIn ? "translate-x-5" : ""}`} />
                </button>
              </div>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">{privacyIntelligenceMock.contributionSettings.anonymizationLevel}</p>
            </div>
          </div>
        </header>

        <section className="grid gap-5 lg:grid-cols-2">
          <LayerCard
            icon={<LockKeyhole className="h-5 w-5" />}
            title="Personal Intelligence"
            subtitle="Private, local, user-specific reasoning"
            items={privacyIntelligenceMock.architectureLayers.personalIntelligence}
          />
          <LayerCard
            icon={<Globe2 className="h-5 w-5" />}
            title="Global Intelligence"
            subtitle="Anonymized aggregate pattern learning"
            items={privacyIntelligenceMock.architectureLayers.globalIntelligence}
          />
        </section>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <main className="space-y-4">
            <div>
              <h2 className="text-xl font-semibold">Recommendations with separated evidence</h2>
              <p className="mt-1 text-sm text-muted-foreground">Every recommendation distinguishes private personal evidence from generalized community patterns.</p>
            </div>
            {privacyIntelligenceMock.recommendations.map((recommendation) => (
              <article key={recommendation.id} className="rounded-lg border border-border bg-white p-5 shadow-soft">
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <h3 className="text-lg font-semibold">{recommendation.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-stone-700">{recommendation.recommendation}</p>
                  </div>
                  <div className="flex gap-2">
                    <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">Impact {recommendation.expectedImpact}</span>
                    <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{Math.round(recommendation.confidence * 100)}%</span>
                  </div>
                </div>

                <div className="mt-4 rounded-md bg-surface p-3">
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Reasoning</p>
                  <p className="mt-1 text-sm leading-6 text-stone-700">{recommendation.reasoning}</p>
                </div>

                <div className="mt-4 grid gap-4 lg:grid-cols-2">
                  <EvidencePanel title="Personal evidence" icon={<LockKeyhole className="h-4 w-4" />} items={recommendation.personalEvidence.map((item) => `${item.title}: ${item.summary}`)} />
                  <EvidencePanel title="Generalized community patterns" icon={<UsersRound className="h-4 w-4" />} items={recommendation.globalPatterns.map((item) => `${item.title}: ${item.sampleSize} anonymous samples, ${item.outcomeLift > 0 ? "+" : ""}${item.outcomeLift}% lift`)} />
                </div>

                <div className="mt-4 rounded-md border border-emerald-100 bg-emerald-50 p-3">
                  <p className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
                    <EyeOff className="h-4 w-4" />
                    Privacy explanation
                  </p>
                  <p className="mt-1 text-sm leading-6 text-emerald-800">{recommendation.privacyExplanation}</p>
                </div>
              </article>
            ))}
          </main>

          <aside className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Network className="h-5 w-5" />
                Shared vs local signals
              </h2>
              <EvidencePanel title="Always local" items={privacyIntelligenceMock.contributionSettings.localOnlySignals} />
              <EvidencePanel title="Anonymous aggregate only" items={privacyIntelligenceMock.contributionSettings.sharedAggregateSignals} className="mt-4" />
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="text-lg font-semibold">Global patterns</h2>
              <div className="mt-3 space-y-3">
                {privacyIntelligenceMock.globalPatterns.map((pattern) => (
                  <article key={pattern.id} className="rounded-md bg-surface p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold">{pattern.title}</p>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-stone-700">{pattern.sampleSize}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{pattern.summary}</p>
                    <p className="mt-2 text-xs text-stone-500">{pattern.anonymization}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="text-lg font-semibold">Privacy guarantees</h2>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-stone-700">
                {privacyIntelligenceMock.privacyGuarantees.map((guarantee) => <li key={guarantee}>{guarantee}</li>)}
              </ul>
              <Button className="mt-4 w-full" variant="outline" onClick={() => setOptedIn(false)}>
                Opt out locally
              </Button>
            </section>
          </aside>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <h2 className="text-lg font-semibold">Audit trail</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {privacyIntelligenceMock.auditTrail.map((event) => (
              <article key={event.id} className="rounded-md bg-surface p-3">
                <p className="text-sm font-semibold">{event.event}</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{event.description}</p>
                <p className="mt-2 text-xs text-stone-500">{event.dataBoundary}</p>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function LayerCard({ icon, title, subtitle, items }: { icon: React.ReactNode; title: string; subtitle: string; items: string[] }) {
  return (
    <article className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-lg font-semibold">{title}</h2>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {items.map((item) => <span key={item} className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{item}</span>)}
      </div>
    </article>
  );
}

function EvidencePanel({ title, items, icon, className }: { title: string; items: string[]; icon?: React.ReactNode; className?: string }) {
  return (
    <div className={className}>
      <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.12em] text-muted">{icon}{title}</p>
      <ul className="mt-2 space-y-2 text-sm leading-6 text-stone-700">
        {items.map((item) => <li key={item} className="rounded-md bg-white/70 px-3 py-2">{item}</li>)}
      </ul>
    </div>
  );
}

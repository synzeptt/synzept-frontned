"use client";

import { BrainCircuit, CheckCircle2, FileText, Lightbulb, MessageSquareText, Route, ShieldAlert } from "lucide-react";
import { reasoningEngineMock } from "@/lib/reasoning-engine/mock-data";

export function ReasoningEngineView() {
  return (
    <div className="min-h-full bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-muted">
            <BrainCircuit className="h-4 w-4" />
            Sprint 2 Reasoning Engine
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">Reason first, compose second</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
            The engine builds a structured response plan before any language model receives context, evidence, and guardrails.
          </p>
        </header>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <main className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Route className="h-5 w-5" />
                Pipeline
              </h2>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {reasoningEngineMock.pipeline.map((step, index) => (
                  <article key={step.component} className="rounded-lg border border-border bg-surface p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Step {index + 1}</p>
                        <h3 className="mt-1 text-sm font-semibold">{step.name}</h3>
                      </div>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{Math.round(step.confidence * 100)}%</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{step.summary}</p>
                    <p className="mt-3 text-xs text-zinc-500">{step.component}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="grid gap-5 lg:grid-cols-2">
              <Panel title="Evidence" icon={<FileText className="h-5 w-5" />}>
                {reasoningEngineMock.evidence.map((item) => (
                  <Item key={item.id} title={item.claim} meta={`${item.source} - ${Math.round(item.strength * 100)}%`} />
                ))}
              </Panel>
              <Panel title="Risks" icon={<ShieldAlert className="h-5 w-5" />}>
                {reasoningEngineMock.risks.map((risk) => (
                  <Item key={risk.id} title={risk.title} meta={`${risk.severity} - ${risk.mitigation}`} />
                ))}
              </Panel>
            </section>
          </main>

          <aside className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <CheckCircle2 className="h-5 w-5" />
                Planner Output
              </h2>
              <div className="mt-3 space-y-3">
                <Fact label="Enough information" value={reasoningEngineMock.plan.hasEnoughInformation ? "Yes" : "No"} />
                <Fact label="Clarification" value={reasoningEngineMock.plan.clarificationNeeded ? "Needed" : "Not needed"} />
                <Fact label="Strategy" value={reasoningEngineMock.plan.responseStrategy} />
              </div>
              <p className="mt-4 rounded-md bg-surface p-3 text-sm leading-6 text-zinc-700">{reasoningEngineMock.plan.recommendation}</p>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <MessageSquareText className="h-5 w-5" />
                LLM Handoff
              </h2>
              <p className="mt-2 rounded-full bg-zinc-100 px-3 py-1 text-xs text-zinc-700">{reasoningEngineMock.llmHandoff.role}</p>
              <div className="mt-3 space-y-2">
                {reasoningEngineMock.llmHandoff.guardrails.map((guardrail) => (
                  <p key={guardrail} className="rounded-md bg-surface p-3 text-sm text-zinc-700">{guardrail}</p>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Lightbulb className="h-5 w-5" />
                Opportunity
              </h2>
              {reasoningEngineMock.opportunities.map((opportunity) => (
                <Item key={opportunity.id} title={opportunity.title} meta={opportunity.rationale} />
              ))}
            </section>
          </aside>
        </section>
      </div>
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        {icon}
        {title}
      </h2>
      <div className="mt-3 space-y-3">{children}</div>
    </section>
  );
}

function Item({ title, meta }: { title: string; meta: string }) {
  return (
    <article className="rounded-md bg-surface p-3">
      <p className="text-sm font-semibold">{title}</p>
      <p className="mt-1 text-sm leading-6 text-muted-foreground">{meta}</p>
    </article>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md bg-surface px-3 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

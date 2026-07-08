"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, ClipboardCheck, HelpCircle, Scale, ScaleIcon, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { decisionSimulationMock } from "@/lib/decision-simulator/mock-data";
import type { DecisionScenario } from "@/lib/decision-simulator/types";

const metrics = [
  { key: "effort", label: "Effort" },
  { key: "risk", label: "Risk" },
  { key: "cost", label: "Cost" },
  { key: "time", label: "Time" },
  { key: "goalAlignment", label: "Goal alignment" },
  { key: "expectedImpact", label: "Expected impact" },
] as const;

export function DecisionSimulatorView() {
  const [selectedScenarioId, setSelectedScenarioId] = useState(decisionSimulationMock.finalChoice?.scenarioId ?? decisionSimulationMock.scenarios[0].id);
  const [recordedChoice, setRecordedChoice] = useState(decisionSimulationMock.finalChoice);
  const selectedScenario = useMemo(
    () => decisionSimulationMock.scenarios.find((scenario) => scenario.id === selectedScenarioId) ?? decisionSimulationMock.scenarios[0],
    [selectedScenarioId],
  );

  return (
    <div className="space-y-5">
      <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Simulation Target</p>
            <h2 className="mt-2 text-2xl font-semibold">{decisionSimulationMock.inputContext.decisionTitle}</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
              Explore plausible futures using personal knowledge, Decision Graph connections, goals, missions, projects, memories, risk preference, and past outcomes.
            </p>
          </div>
          <div className="rounded-md bg-surface px-3 py-2 text-sm text-stone-700">{decisionSimulationMock.inputContext.riskPreference}</div>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-3">
          <ContextBlock title="Graph connections" items={decisionSimulationMock.inputContext.decisionGraphConnections} />
          <ContextBlock title="Goals and missions" items={[...decisionSimulationMock.inputContext.goals, ...decisionSimulationMock.inputContext.missions]} />
          <ContextBlock title="Past outcome signals" items={decisionSimulationMock.inputContext.pastOutcomeSignals} />
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        {decisionSimulationMock.scenarios.map((scenario) => (
          <ScenarioCard
            key={scenario.id}
            scenario={scenario}
            selected={scenario.id === selectedScenarioId}
            chosen={recordedChoice?.scenarioId === scenario.id}
            onSelect={() => setSelectedScenarioId(scenario.id)}
            onChoose={() => {
              setSelectedScenarioId(scenario.id);
              setRecordedChoice({
                scenarioId: scenario.id,
                chosenAt: new Date().toISOString(),
                rationale: `Mock choice recorded for ${scenario.title}.`,
                status: "recorded_mock",
              });
            }}
          />
        ))}
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex items-center gap-2">
            <Scale className="h-5 w-5" />
            <h2 className="text-lg font-semibold">Side-by-side comparison</h2>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[760px] border-separate border-spacing-0 text-sm">
              <thead>
                <tr>
                  <th className="border-b border-border px-3 py-2 text-left font-medium text-muted-foreground">Metric</th>
                  {decisionSimulationMock.scenarios.map((scenario) => (
                    <th key={scenario.id} className="border-b border-border px-3 py-2 text-left font-medium text-stone-900">{scenario.title}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.map((metric) => (
                  <tr key={metric.key}>
                    <td className="border-b border-border px-3 py-3 font-medium text-stone-700">{metric.label}</td>
                    {decisionSimulationMock.scenarios.map((scenario) => (
                      <td key={scenario.id} className="border-b border-border px-3 py-3">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-24 overflow-hidden rounded-full bg-stone-100">
                            <div className="h-full rounded-full bg-stone-900" style={{ width: `${scenario.comparison[metric.key]}%` }} />
                          </div>
                          <span>{scenario.comparison[metric.key]}</span>
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="space-y-5">
          <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <div className="flex items-center gap-2">
              <ClipboardCheck className="h-5 w-5" />
              <h2 className="text-lg font-semibold">Selected Scenario</h2>
            </div>
            <p className="mt-3 text-base font-semibold">{selectedScenario.title}</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">{selectedScenario.summary}</p>
            <div className="mt-4 rounded-md bg-surface p-3">
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Best case</p>
              <p className="mt-1 text-sm leading-6 text-stone-700">{selectedScenario.bestCaseOutcome}</p>
            </div>
            <div className="mt-3 rounded-md bg-surface p-3">
              <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Worst case</p>
              <p className="mt-1 text-sm leading-6 text-stone-700">{selectedScenario.worstCaseOutcome}</p>
            </div>
          </section>

          {recordedChoice && (
            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5" />
                <h2 className="text-lg font-semibold">Final Choice</h2>
              </div>
              <p className="mt-3 text-sm leading-6 text-stone-700">{recordedChoice.rationale}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.12em] text-muted">{recordedChoice.status}</p>
            </section>
          )}

          {decisionSimulationMock.learning && (
            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                <h2 className="text-lg font-semibold">Learning Review</h2>
              </div>
              <p className="mt-3 text-sm font-medium text-stone-700">Accuracy {decisionSimulationMock.learning.accuracy}%</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{decisionSimulationMock.learning.actualResult}</p>
              <ul className="mt-3 space-y-1.5 text-sm leading-6 text-stone-700">
                {decisionSimulationMock.learning.lessonsLearned.map((lesson) => <li key={lesson}>{lesson}</li>)}
              </ul>
            </section>
          )}
        </aside>
      </section>
    </div>
  );
}

function ScenarioCard({
  scenario,
  selected,
  chosen,
  onSelect,
  onChoose,
}: {
  scenario: DecisionScenario;
  selected: boolean;
  chosen: boolean;
  onSelect: () => void;
  onChoose: () => void;
}) {
  return (
    <article className={cn("rounded-lg border bg-white p-4 shadow-soft", selected ? "border-stone-900" : "border-border")}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold leading-6">{scenario.title}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{scenario.summary}</p>
        </div>
        {chosen && <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700">Chosen</span>}
      </div>
      <div className="mt-4 grid gap-3">
        <MiniList title="Benefits" items={scenario.potentialBenefits} />
        <MiniList title="Risks" items={scenario.potentialRisks} />
        <MiniList title="Assumptions" items={scenario.assumptions} icon={<HelpCircle className="h-4 w-4" />} />
      </div>
      <div className="mt-4 flex items-center justify-between gap-3">
        <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">Confidence {Math.round(scenario.confidence * 100)}%</span>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={onSelect}>Inspect</Button>
          <Button size="sm" onClick={onChoose}>
            <ScaleIcon className="mr-2 h-4 w-4" />
            Choose
          </Button>
        </div>
      </div>
    </article>
  );
}

function ContextBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-md bg-surface p-3">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{title}</p>
      <ul className="mt-2 space-y-1.5 text-sm leading-5 text-stone-700">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

function MiniList({ title, items, icon }: { title: string; items: string[]; icon?: React.ReactNode }) {
  return (
    <div>
      <p className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-[0.12em] text-muted">{icon}{title}</p>
      <ul className="mt-2 space-y-1.5 text-sm leading-5 text-stone-700">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </div>
  );
}

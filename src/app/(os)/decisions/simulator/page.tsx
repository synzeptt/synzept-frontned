import { PageFrame } from "@frontend/components/layout/page-frame";
import { DecisionShell } from "@/components/decision-intelligence/DecisionShell";
import { DecisionSimulatorView } from "@/components/decision-simulator/DecisionSimulatorView";

export default function DecisionSimulatorPage() {
  return (
    <PageFrame eyebrow="Decision Intelligence" title="Decision Simulator">
      <DecisionShell active="Simulator">
        <DecisionSimulatorView />
      </DecisionShell>
    </PageFrame>
  );
}

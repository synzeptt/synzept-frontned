import { PageFrame } from "@frontend/components/layout/page-frame";
import { DecisionShell } from "@/components/decision-intelligence/DecisionShell";
import { DecisionGraphView } from "@/components/decision-graph/DecisionGraphView";

export default function DecisionGraphPage() {
  return (
    <PageFrame eyebrow="Decision Intelligence" title="Decision Graph">
      <DecisionShell active="Graph">
        <DecisionGraphView />
      </DecisionShell>
    </PageFrame>
  );
}

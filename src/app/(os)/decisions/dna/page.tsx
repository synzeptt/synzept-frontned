import { PageFrame } from "@frontend/components/layout/page-frame";
import { DecisionShell } from "@/components/decision-intelligence/DecisionShell";
import { DNATraitCard } from "@/components/decision-intelligence/DecisionPrimitives";
import { decisionIntelligenceMock } from "@/lib/decision-intelligence/mock-data";

export default function DecisionDNAPage() {
  return (
    <PageFrame eyebrow="Decision Intelligence" title="Decision DNA">
      <DecisionShell active="Decision DNA">
        <section className="grid gap-4 lg:grid-cols-2">
          {decisionIntelligenceMock.decisionDNA.map((trait) => <DNATraitCard key={trait.id} trait={trait} />)}
        </section>
      </DecisionShell>
    </PageFrame>
  );
}

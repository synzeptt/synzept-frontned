import { PageFrame } from "@frontend/components/layout/page-frame";
import { ReasoningEngineView } from "@/components/reasoning-engine/ReasoningEngineView";

export default function ReasoningEnginePage() {
  return (
    <PageFrame eyebrow="Sprint 2" title="Reasoning Engine">
      <ReasoningEngineView />
    </PageFrame>
  );
}

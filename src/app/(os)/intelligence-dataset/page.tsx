import { PageFrame } from "@frontend/components/layout/page-frame";
import { IntelligenceDatasetView } from "@/components/intelligence-dataset/IntelligenceDatasetView";

export default function IntelligenceDatasetPage() {
  return (
    <PageFrame eyebrow="Sprint 1" title="Intelligence Dataset">
      <IntelligenceDatasetView />
    </PageFrame>
  );
}

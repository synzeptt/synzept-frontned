import { PageFrame } from "@frontend/components/layout/page-frame";
import { PrivacyIntelligenceView } from "@/components/privacy-intelligence/PrivacyIntelligenceView";

export default function PrivacyNetworkPage() {
  return (
    <PageFrame eyebrow="Privacy Intelligence" title="Privacy Network">
      <PrivacyIntelligenceView />
    </PageFrame>
  );
}

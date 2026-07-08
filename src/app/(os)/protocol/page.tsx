import { PageFrame } from "@frontend/components/layout/page-frame";
import { SynzeptProtocolView } from "@/components/synzept-protocol/SynzeptProtocolView";

export default function ProtocolPage() {
  return (
    <PageFrame eyebrow="Platform Protocol" title="Synzept Protocol">
      <SynzeptProtocolView />
    </PageFrame>
  );
}

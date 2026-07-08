"use client";

import { PageFrame } from "@frontend/components/layout/page-frame";
import { WorkspaceHome } from "@/components/workspace-os/WorkspaceHome";

export default function DashboardPage() {
  return (
    <PageFrame eyebrow="Workspace OS" title="Home">
      <WorkspaceHome />
    </PageFrame>
  );
}

import { PageFrame } from "@frontend/components/layout/page-frame";
import { WorkspaceSearch } from "@/components/workspace-os/WorkspaceSearch";

export default function SearchPage() {
  return (
    <PageFrame eyebrow="Workspace OS" title="Search">
      <div className="min-h-full bg-stone-50 p-4 sm:p-6">
        <div className="mx-auto max-w-5xl rounded-lg border border-border bg-white p-4 shadow-soft sm:p-5">
          <WorkspaceSearch />
        </div>
      </div>
    </PageFrame>
  );
}

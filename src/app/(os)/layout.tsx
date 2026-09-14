import { Suspense } from "react";
import { AppShell } from "@/components/layout/app-shell";

export default function OSLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-[#f7f4ee] text-sm text-stone-600">Loading workspace…</div>}>
      <AppShell>{children}</AppShell>
    </Suspense>
  );
}

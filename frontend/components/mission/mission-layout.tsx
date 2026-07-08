import type { ReactNode } from "react";

export function MissionLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-full bg-stone-50 text-stone-950">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">{children}</div>
      </div>
    </div>
  );
}

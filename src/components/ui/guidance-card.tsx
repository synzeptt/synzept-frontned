import type { ReactNode } from "react";
import { Info } from "lucide-react";
import { cn } from "@/lib/cn";

export function GuidanceCard({
  title,
  children,
  icon,
  className,
}: {
  title: string;
  children: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <aside className={cn("rounded-lg border border-border bg-stone-50 px-4 py-3 text-sm leading-6 text-stone-600", className)}>
      <p className="mb-1 flex items-center gap-2 font-medium text-stone-900">
        <span className="text-stone-500">{icon || <Info className="h-4 w-4" />}</span>
        {title}
      </p>
      {children}
    </aside>
  );
}

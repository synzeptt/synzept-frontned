import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function EmptyState({
  icon,
  title,
  description,
  steps,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description: string;
  steps?: string[];
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-white px-6 py-10 text-center shadow-soft",
        className,
      )}
    >
      {icon && (
        <div className="mx-auto mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-accent-muted text-accent">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold text-stone-950">{title}</h3>
      <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">{description}</p>
      {!!steps?.length && (
        <div className="mx-auto mt-4 grid max-w-lg gap-2 text-left">
          {steps.slice(0, 3).map((step) => (
            <p key={step} className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-5 text-stone-600">
              {step}
            </p>
          ))}
        </div>
      )}
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </div>
  );
}

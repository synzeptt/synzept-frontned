import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export type HighestPriorityProps = {
  title: string;
  reason: string;
  impact: string;
  actionLabel: string;
  onContinue?: () => void;
};

export function HighestPriority({ title, reason, impact, actionLabel, onContinue }: HighestPriorityProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl space-y-4">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Today’s highest priority</p>
          <h2 className="text-3xl font-semibold tracking-tight text-stone-950">{title}</h2>
          <p className="text-base leading-7 text-stone-600">{reason}</p>
          <div className="inline-flex items-center rounded-full bg-stone-100 px-4 py-2 text-sm font-medium text-stone-700">{impact}</div>
        </div>
        <Button onClick={onContinue} size="lg" className="w-full justify-center lg:w-auto">
          {actionLabel}
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </section>
  );
}

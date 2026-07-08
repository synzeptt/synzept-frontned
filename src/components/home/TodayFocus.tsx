import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export type TodayFocusProps = {
  title: string;
  currentFocus: string;
  description: string;
  onContinue: () => void;
};

export function TodayFocus({ title, currentFocus, description, onContinue }: TodayFocusProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">{title}</p>
          <h2 className="mt-4 max-w-2xl text-3xl font-semibold leading-tight text-stone-950 sm:text-4xl">{currentFocus}</h2>
        </div>
        <Button onClick={onContinue} className="h-11 px-6" aria-label="Continue Working">
          Continue Working
          <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
      <p className="mt-5 max-w-xl text-sm leading-7 text-stone-600">{description}</p>
    </section>
  );
}

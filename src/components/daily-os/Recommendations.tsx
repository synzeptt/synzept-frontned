import { Button } from "@/components/ui/button";

export type DailyOSRecommendation = {
  id: string;
  title: string;
  reason: string;
  benefit: string;
  actionLabel: string;
};

export type RecommendationsProps = {
  items: DailyOSRecommendation[];
  onAction?: (id: string) => void;
};

export function Recommendations({ items, onAction }: RecommendationsProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Recommendations</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">What to do next</h2>
      </div>
      <div className="mt-6 grid gap-4">
        {items.map((item) => (
          <article key={item.id} className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-2">
                <p className="text-base font-semibold text-stone-950">{item.title}</p>
                <p className="text-sm leading-6 text-stone-700">{item.reason}</p>
                <p className="text-sm font-medium text-stone-900">Expected benefit: {item.benefit}</p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="mt-4 w-full justify-center sm:mt-0 sm:w-auto"
                onClick={() => onAction?.(item.id)}
              >
                {item.actionLabel}
              </Button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

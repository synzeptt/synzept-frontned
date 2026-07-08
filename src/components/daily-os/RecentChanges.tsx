import { CheckCircle2, Circle } from "lucide-react";

export type RecentChangeItem = {
  id: string;
  text: string;
  completed: boolean;
};

export type RecentChangesProps = {
  items: RecentChangeItem[];
};

export function RecentChanges({ items }: RecentChangesProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Since your last visit</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">What changed</h2>
      </div>
      <div className="mt-6 grid gap-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-3xl border border-stone-200 bg-stone-50 p-4">
            <div className="flex items-start gap-3">
              {item.completed ? (
                <CheckCircle2 className="mt-1 h-5 w-5 text-emerald-600" />
              ) : (
                <Circle className="mt-1 h-4 w-4 text-stone-400" />
              )}
              <p className="text-sm leading-6 text-stone-700">{item.text}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export type SinceLastVisitItem = {
  id: string;
  text: string;
  completed?: boolean;
};

export type SinceLastVisitProps = {
  items: SinceLastVisitItem[];
};

export function SinceLastVisit({ items }: SinceLastVisitProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Since your last visit</p>
          <h2 className="mt-3 text-2xl font-semibold text-stone-950">What changed</h2>
        </div>
      </div>
      <ul className="mt-6 space-y-4">
        {items.map((item) => (
          <li key={item.id} className="flex items-start gap-3 text-sm leading-6 text-stone-700">
            <span className={`mt-1 inline-flex h-2.5 w-2.5 rounded-full ${item.completed ? "bg-emerald-500" : "bg-stone-400"}`} />
            <span>{item.text}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

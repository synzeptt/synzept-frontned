export type ProgressOverviewItem = {
  id: string;
  area: string;
  detail: string;
  value: string;
};

export type ProgressOverviewProps = {
  items: ProgressOverviewItem[];
};

export function ProgressOverview({ items }: ProgressOverviewProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Progress</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">What’s moving forward</h2>
      </div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {items.map((item) => (
          <div key={item.id} className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
            <p className="text-sm font-semibold text-stone-950">{item.area}</p>
            <p className="mt-3 text-sm leading-6 text-stone-600">{item.detail}</p>
            <p className="mt-4 text-lg font-semibold text-stone-950">{item.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

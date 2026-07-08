export type DailyOSInsight = {
  id: string;
  title: string;
  detail: string;
};

export type InsightsProps = {
  insights: DailyOSInsight[];
};

export function Insights({ insights }: InsightsProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">AI Insights</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">What Synzept noticed</h2>
      </div>
      <div className="mt-6 grid gap-4">
        {insights.map((insight) => (
          <article key={insight.id} className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
            <p className="text-sm font-semibold text-stone-950">{insight.title}</p>
            <p className="mt-3 text-sm leading-6 text-stone-700">{insight.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

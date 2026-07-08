export type DailyOSOpenLoop = {
  id: string;
  title: string;
  priority: "High" | "Medium" | "Low";
  lastUpdated: string;
  nextStep: string;
};

export type DailyOSOpenLoopsProps = {
  loops: DailyOSOpenLoop[];
};

function priorityClass(priority: DailyOSOpenLoop["priority"]) {
  return priority === "High"
    ? "bg-amber-100 text-amber-800"
    : priority === "Medium"
    ? "bg-sky-100 text-sky-800"
    : "bg-stone-100 text-stone-800";
}

export function OpenLoops({ loops }: DailyOSOpenLoopsProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Open loops</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">Unfinished work to keep in view</h2>
      </div>
      <div className="mt-6 space-y-4">
        {loops.map((loop) => (
          <article key={loop.id} className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-base font-semibold text-stone-950">{loop.title}</h3>
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${priorityClass(loop.priority)}`}>{loop.priority}</span>
            </div>
            <p className="mt-3 text-sm leading-6 text-stone-600">Last updated {loop.lastUpdated}</p>
            <p className="mt-4 text-sm leading-6 text-stone-700">Suggested next step: {loop.nextStep}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

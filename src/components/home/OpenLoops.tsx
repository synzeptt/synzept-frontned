export type OpenLoopItem = {
  id: string;
  title: string;
};

export type OpenLoopsProps = {
  loops: OpenLoopItem[];
};

export function OpenLoops({ loops }: OpenLoopsProps) {
  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Open loops</p>
          <h2 className="mt-3 text-2xl font-semibold text-stone-950">Unfinished work to keep in view</h2>
        </div>
      </div>
      <ul className="mt-6 space-y-3 text-sm leading-6 text-stone-700">
        {loops.map((loop) => (
          <li key={loop.id} className="rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3">
            {loop.title}
          </li>
        ))}
      </ul>
    </section>
  );
}

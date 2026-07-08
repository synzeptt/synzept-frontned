export type ProgressHeaderProps = {
  step: number;
  total: number;
  label: string;
};

export function ProgressHeader({ step, total, label }: ProgressHeaderProps) {
  return (
    <div className="flex flex-col gap-3 rounded-[32px] border border-stone-200 bg-white px-6 py-5 shadow-soft sm:px-8 sm:py-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-400">Step {step} of {total}</p>
        <p className="text-sm text-stone-500">{label}</p>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-stone-100">
        <div className="h-full rounded-full bg-stone-950" style={{ width: `${(step / total) * 100}%` }} />
      </div>
    </div>
  );
}

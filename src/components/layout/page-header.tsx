export function PageHeader({
  label,
  title,
  action,
}: {
  label?: string;
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <header className="flex shrink-0 items-end justify-between border-b border-border px-6 py-5 md:px-8">
      <div>
        {label && (
          <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-muted">{label}</p>
        )}
        <h1 className="mt-1 text-xl font-semibold tracking-tight text-stone-950 md:text-2xl">{title}</h1>
      </div>
      {action}
    </header>
  );
}

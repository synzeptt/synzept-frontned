export function PageFrame({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow: string;
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex h-full flex-col">
      <header className="flex min-h-16 shrink-0 items-center justify-between gap-3 border-b border-border bg-white/80 px-4 backdrop-blur md:px-7">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground">{eyebrow}</p>
          <h1 className="truncate text-lg font-semibold text-stone-950">{title}</h1>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}

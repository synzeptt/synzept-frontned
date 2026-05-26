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
      <header className="flex min-h-16 shrink-0 items-center justify-between border-b border-border bg-white/80 px-5 backdrop-blur md:px-7">
        <div>
          <p className="text-xs text-muted-foreground">{eyebrow}</p>
          <h1 className="text-lg font-semibold text-stone-950">{title}</h1>
        </div>
        {action}
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}

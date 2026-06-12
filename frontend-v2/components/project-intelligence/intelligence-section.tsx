export function IntelligenceSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-white px-5 py-5">
      <h2 className="text-base font-semibold text-stone-950">{title}</h2>
      {description && <p className="mt-1 text-sm leading-6 text-stone-500">{description}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

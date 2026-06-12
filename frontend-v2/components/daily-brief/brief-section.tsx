type BriefSectionProps = {
  title: string;
  description?: string;
  children: React.ReactNode;
};

export function BriefSection({ title, description, children }: BriefSectionProps) {
  return (
    <section className="border-b border-border py-6 last:border-0">
      <h2 className="text-base font-semibold text-stone-950">{title}</h2>
      {description && <p className="mt-1 text-sm leading-6 text-stone-500">{description}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

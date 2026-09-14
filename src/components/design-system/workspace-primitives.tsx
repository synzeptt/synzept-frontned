import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function Page({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("min-h-full bg-[var(--background)] text-[var(--text-primary)]", className)}>{children}</div>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <header className={cn("flex items-start justify-between gap-6", className)}>
      <div className="min-w-0">
        {eyebrow ? <p className="synzept-eyebrow mb-3">{eyebrow}</p> : null}
        <h1 className="text-[var(--type-h1)] font-semibold leading-[1.14] tracking-[-0.035em] text-[var(--text-primary)]">{title}</h1>
        {description ? <p className="mt-2 max-w-xl text-[var(--type-body)] leading-6 text-[var(--text-secondary)]">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </header>
  );
}

export function Surface({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("rounded-xl border border-[var(--border)] bg-[var(--surface-elevated)]", className)}>{children}</div>;
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)] p-5", className)}>{children}</div>;
}

export function Section({ children, className }: { children: ReactNode; className?: string }) {
  return <section className={cn("border-y border-[var(--border)] bg-transparent", className)}>{children}</section>;
}

export function SettingsSection({ title, description, children, action }: { title: string; description?: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <section className="border-y border-[var(--border)] bg-transparent py-5 sm:py-6">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">{title}</p>
          {description ? <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--text-secondary)]">{description}</p> : null}
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      {children ? <div className="space-y-3">{children}</div> : null}
    </section>
  );
}

export function SettingsRow({ label, description, action, children, className }: { label: string; description?: string; action?: ReactNode; children?: ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-3 border-t border-[var(--border)] px-0 py-4 sm:flex-row sm:items-center sm:justify-between", className)}>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-[var(--text-primary)]">{label}</p>
        {description ? <p className="mt-1 text-xs leading-5 text-[var(--text-muted)]">{description}</p> : null}
      </div>
      {children ? <div className="shrink-0">{children}</div> : null}
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function SectionHeader({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-5">
      <div>
        <h2 className="text-base font-semibold tracking-[-0.015em] text-[var(--text-primary)]">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">{description}</p> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function Row({ children, href, onClick, className }: { children: ReactNode; href?: string; onClick?: () => void; className?: string }) {
  const classes = cn("flex w-full items-center justify-between gap-6 border-t border-[var(--border)] py-4 text-left transition hover:bg-[var(--surface-subtle)]", className);
  if (href) return <a href={href} className={classes}>{children}</a>;
  return <button type="button" onClick={onClick} className={classes}>{children}</button>;
}

export function Metadata({ children }: { children: ReactNode }) {
  return <span className="text-xs leading-5 text-[var(--text-muted)]">{children}</span>;
}

export function Status({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "success" | "warning" | "error" }) {
  return <span className={cn("text-xs font-medium", tone === "success" && "text-[var(--success)]", tone === "warning" && "text-[var(--warning)]", tone === "error" && "text-[var(--danger)]", tone === "neutral" && "text-[var(--text-muted)]")}>{children}</span>;
}

export function CommandSurface({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("rounded-2xl border border-[var(--border)] bg-[var(--surface-elevated)] transition-colors focus-within:border-[var(--border-strong)] focus-within:shadow-[0_0_0_3px_rgb(var(--color-accent)/0.08)]", className)}>{children}</div>;
}

export function Stack({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex flex-col gap-4", className)}>{children}</div>;
}

export function Inline({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("flex items-center gap-3", className)}>{children}</div>;
}

export function Divider({ className }: { className?: string }) {
  return <div className={cn("h-px w-full bg-[var(--border)]", className)} />;
}

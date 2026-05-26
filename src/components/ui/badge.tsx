import { cn } from "@/lib/cn";

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: React.ReactNode;
  variant?: "default" | "accent" | "muted";
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        variant === "accent" && "bg-accent-muted text-accent-foreground",
        variant === "muted" && "bg-stone-100 text-muted-foreground",
        variant === "default" && "bg-stone-100 text-stone-600",
        className,
      )}
    >
      {children}
    </span>
  );
}

import { cn } from "@/lib/utils";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: "default" | "primary" | "success" }) {
  const variants = {
    default: "bg-secondary text-muted-foreground",
    primary: "bg-primary/15 text-primary border border-primary/20",
    success: "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20"
  };
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium", variants[variant], className)} {...props} />
  );
}

import { cn } from "@/lib/cn";

export function Progress({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cn("h-3 overflow-hidden rounded-full bg-stone-200", className)}>
      <div className="h-full rounded-full bg-accent transition-all duration-300" style={{ width: `${value}%` }} />
    </div>
  );
}

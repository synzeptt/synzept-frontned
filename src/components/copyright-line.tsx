import { cn } from "@/lib/cn";

export function CopyrightLine({ className }: { className?: string }) {
  return (
    <p className={cn("text-[11px] leading-relaxed text-muted", className)}>
      © 2026 Synzept AI. All rights reserved.
    </p>
  );
}

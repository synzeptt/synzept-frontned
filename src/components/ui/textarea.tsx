import * as React from "react";
import { cn } from "@/lib/cn";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "w-full rounded-lg border border-border bg-white px-4 py-3 text-sm text-stone-900 outline-none transition placeholder:text-muted focus:border-accent/40 focus:ring-2 focus:ring-accent/10",
        className,
      )}
      {...props}
    />
  ),
);
Textarea.displayName = "Textarea";

import * as React from "react";
import { cn } from "@/lib/cn";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-lg border border-border bg-white px-3.5 text-sm text-stone-900 outline-none transition placeholder:text-muted focus:border-accent/40 focus:ring-2 focus:ring-accent/10",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";

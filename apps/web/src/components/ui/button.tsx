import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "default" | "primary" | "secondary" | "ghost" | "outline" | "danger";
  size?: "default" | "sm" | "lg" | "icon";
};

const variants = {
  default: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  primary: "bg-primary text-primary-foreground hover:bg-primary/90 shadow-glow",
  secondary: "bg-secondary/80 text-secondary-foreground hover:bg-secondary",
  ghost: "hover:bg-secondary/60 text-muted-foreground hover:text-foreground",
  outline: "border border-border bg-transparent hover:bg-secondary/50",
  danger: "bg-red-500/10 text-red-300 border border-red-500/20 hover:bg-red-500/20"
};

const sizes = {
  default: "h-9 px-4 py-2",
  sm: "h-8 px-3 text-xs",
  lg: "h-11 px-6",
  icon: "h-9 w-9 p-0"
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg text-sm font-medium transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  )
);
Button.displayName = "Button";

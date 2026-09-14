import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export const WORKSPACE_CONTENT_MAX_WIDTH = "1088px";
export const WORKSPACE_CONTENT_PADDING = {
  base: "24px",
  sm: "40px",
  lg: "56px",
};
export const WORKSPACE_PAGE_TOP_PADDING = {
  base: "32px",
  sm: "40px",
  lg: "48px",
};
const workspaceContentClassName = "mx-auto w-full max-w-[1088px] px-6 sm:px-10 lg:px-14";
const workspacePageClassName = `${workspaceContentClassName} py-8 sm:py-10 lg:py-12`;

export function WorkspaceContent({
  as = "div",
  children,
  className,
}: {
  as?: "div" | "main";
  children: ReactNode;
  className?: string;
}) {
  const Component = as;
  return (
    <Component className={cn(workspaceContentClassName, className)}>
      {children}
    </Component>
  );
}

export function WorkspacePage({
  as = "main",
  children,
  className,
}: {
  as?: "div" | "main";
  children: ReactNode;
  className?: string;
}) {
  const Component = as;
  return (
    <Component className={cn(workspacePageClassName, className)}>
      {children}
    </Component>
  );
}

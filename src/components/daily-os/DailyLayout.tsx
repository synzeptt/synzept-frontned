import { ReactNode } from "react";

export function DailyLayout({ children }: { children: ReactNode }) {
  return <div className="space-y-6">{children}</div>;
}

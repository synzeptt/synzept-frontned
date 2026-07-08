import { type ReactNode } from "react";

export function OnboardingLayout({ children }: { children: ReactNode }) {
  return <div className="min-h-screen bg-stone-50 px-4 py-6 sm:px-6 lg:px-8">{children}</div>;
}

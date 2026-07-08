"use client";

import Link from "next/link";
import { Brain, ChartNoAxesCombined, ClipboardCheck, GitBranch, ListChecks, Network, WandSparkles } from "lucide-react";
import { cn } from "@/lib/cn";

const tabs = [
  { href: "/decisions", label: "Feed", icon: ListChecks },
  { href: "/decisions/simulator", label: "Simulator", icon: WandSparkles },
  { href: "/decisions/graph", label: "Graph", icon: Network },
  { href: "/decisions/reviews", label: "Reviews", icon: ClipboardCheck },
  { href: "/decisions/dna", label: "Decision DNA", icon: Brain },
  { href: "/decisions/analytics", label: "Analytics", icon: ChartNoAxesCombined },
];

export function DecisionShell({ children, active }: { children: React.ReactNode; active: string }) {
  return (
    <div className="min-h-full bg-stone-50 text-stone-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-muted">
                <GitBranch className="h-4 w-4" />
                Decision Intelligence
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">Improve future decisions from past evidence</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
                Capture meaningful decisions, review outcomes, learn decision patterns, and explain future recommendations transparently.
              </p>
            </div>
          </div>
          <nav className="mt-5 flex gap-2 overflow-x-auto pb-1">
            {tabs.map((tab) => (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  "flex h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium",
                  active === tab.label ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-700 hover:bg-stone-200",
                )}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
              </Link>
            ))}
          </nav>
        </header>
        {children}
      </div>
    </div>
  );
}

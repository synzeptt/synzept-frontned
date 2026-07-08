"use client";

import { useMemo } from "react";

export type DailyGreetingProps = {
  name: string;
};

export function DailyGreeting({ name }: DailyGreetingProps) {
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 18) return "Good Afternoon";
    return "Good Evening";
  }, []);

  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div className="max-w-3xl space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Welcome back</p>
        <h1 className="text-3xl font-semibold tracking-tight text-stone-950 sm:text-4xl">{greeting}, {name}</h1>
        <p className="text-base leading-7 text-stone-600">Here’s everything that matters today—your clearest priority, what changed since your last visit, the current state of progress, and the next best action.</p>
      </div>
    </section>
  );
}

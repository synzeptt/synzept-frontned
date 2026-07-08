import { useMemo } from "react";

export type GreetingProps = {
  name: string;
};

export function HomeHeader({ name }: GreetingProps) {
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 18) return "Good Afternoon";
    return "Good Evening";
  }, []);

  return (
    <section className="rounded-[28px] bg-white px-6 py-8 shadow-soft md:px-8 md:py-10">
      <p className="text-sm font-medium uppercase tracking-[0.28em] text-stone-400">Welcome back</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950 sm:text-4xl">{greeting}, {name}</h1>
      <p className="mt-3 max-w-2xl text-base leading-7 text-stone-600">Let’s continue where you left off.</p>
    </section>
  );
}

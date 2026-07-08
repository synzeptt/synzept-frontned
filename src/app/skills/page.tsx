"use client";

import { Search, Sparkles, Star } from "lucide-react";

const skills = [
  {
    name: "Launch Planner",
    category: "Startup",
    description: "Turn a product vision into a crisp launch plan.",
    favorite: true,
  },
  {
    name: "Daily Planning",
    category: "Productivity",
    description: "Turn the day's context into a clear plan.",
    favorite: true,
  },
  {
    name: "Build Knowledge Graph",
    category: "Knowledge",
    description: "Connect related notes, memories, and projects.",
    favorite: false,
  },
  {
    name: "Goal Review",
    category: "Personal",
    description: "Evaluate current goals and the next highest-leverage move.",
    favorite: false,
  },
];

export default function SkillsPage() {
  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-stone-900 p-2 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Skill Library</p>
              <h1 className="text-3xl font-semibold">Reusable workflows for Synzept</h1>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 rounded-2xl border border-stone-200 bg-stone-50 px-3 py-2">
            <Search className="h-4 w-4 text-stone-500" />
            <input placeholder="Search skills" className="w-full bg-transparent text-sm outline-none" />
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Categories</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {['Startup', 'Productivity', 'Knowledge', 'Personal'].map((category) => (
                <span key={category} className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-sm text-stone-600">{category}</span>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Recommended skills</h2>
            <div className="mt-4 space-y-3">
              {skills.map((skill) => (
                <div key={skill.name} className="flex items-start justify-between rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <div>
                    <p className="font-medium">{skill.name}</p>
                    <p className="mt-1 text-sm text-stone-600">{skill.description}</p>
                    <p className="mt-2 text-xs uppercase tracking-[0.2em] text-stone-500">{skill.category}</p>
                  </div>
                  {skill.favorite ? <Star className="h-4 w-4 text-amber-500" /> : null}
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

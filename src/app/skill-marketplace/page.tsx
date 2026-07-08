"use client";

import { Search, Sparkles, Star } from "lucide-react";
import { skillMarketplaceItems } from "./data";

export default function SkillMarketplacePage() {
  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-stone-900 p-2 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Skill Marketplace</p>
              <h1 className="text-3xl font-semibold">Discover, install, and manage AI Skills</h1>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 rounded-2xl border border-stone-200 bg-stone-50 px-3 py-2">
            <Search className="h-4 w-4 text-stone-500" />
            <input placeholder="Search skills" className="w-full bg-transparent text-sm outline-none" />
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Categories</h2>
            <div className="mt-4 flex flex-wrap gap-2">
              {['Startup', 'Productivity', 'Knowledge', 'Personal'].map((category) => (
                <span key={category} className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-sm text-stone-600">{category}</span>
              ))}
            </div>
            <div className="mt-6 rounded-2xl border border-stone-200 bg-stone-50 p-4">
              <p className="text-sm font-semibold">Featured</p>
              <p className="mt-2 text-sm text-stone-600">Launch Planner and Knowledge Graph Builder are highlighted for early adopters.</p>
            </div>
            <div className="mt-6 rounded-2xl border border-stone-200 bg-stone-50 p-4">
              <p className="text-sm font-semibold">Installed</p>
              <p className="mt-2 text-sm text-stone-600">You currently have two active skills and one update ready.</p>
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Marketplace catalog</h2>
            <div className="mt-4 space-y-3">
              {skillMarketplaceItems.map((skill) => (
                <div key={skill.id} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{skill.name}</p>
                      <p className="mt-1 text-sm text-stone-600">{skill.description}</p>
                      <p className="mt-2 text-xs uppercase tracking-[0.2em] text-stone-500">{skill.category} • v{skill.version}</p>
                    </div>
                    <div className="flex items-center gap-1 text-amber-500">
                      <Star className="h-4 w-4" />
                      <span className="text-sm font-medium">{skill.rating}</span>
                    </div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {skill.featured ? <span className="rounded-full bg-stone-900 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-white">Featured</span> : null}
                    {skill.installed ? <span className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">Installed</span> : null}
                    {skill.updateAvailable ? <span className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-amber-700">Update available</span> : null}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-stone-500">
                    <span>Permissions: {skill.permissions.join(", ")}</span>
                    <span>•</span>
                    <span>Integrations: {skill.integrations.join(", ")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

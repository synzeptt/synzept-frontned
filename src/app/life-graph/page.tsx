"use client";

import { useMemo, useState } from "react";
import { Filter, Search, Sparkles, Waypoints } from "lucide-react";

const entities = [
  { id: "mission-1", type: "Mission", title: "Launch Synzept V2" },
  { id: "goal-1", type: "Goal", title: "Improve daily activation" },
  { id: "project-1", type: "Project", title: "Life Graph Engine" },
  { id: "task-1", type: "Task", title: "Implement explorer page" },
  { id: "memory-1", type: "Memory", title: "Daily brief drives activation" },
];

const relationships = [
  { source: "task-1", target: "project-1", type: "belongs_to" },
  { source: "project-1", target: "mission-1", type: "created_from" },
  { source: "memory-1", target: "task-1", type: "related_to" },
];

export default function LifeGraphPage() {
  const [query, setQuery] = useState("");
  const [selectedType, setSelectedType] = useState("All");

  const filteredEntities = useMemo(() => {
    return entities.filter((entity) => {
      const matchesQuery = entity.title.toLowerCase().includes(query.toLowerCase());
      const matchesType = selectedType === "All" || entity.type === selectedType;
      return matchesQuery && matchesType;
    });
  }, [query, selectedType]);

  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-stone-900 p-2 text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Life Graph Explorer</p>
              <h1 className="text-3xl font-semibold">Connected context for every Synzept entity</h1>
            </div>
          </div>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-stone-600">
            Search entities, expand connected nodes, and trace relationship paths across missions, projects, goals, memories, and more.
          </p>
        </header>

        <section className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <label className="flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2">
              <Search className="h-4 w-4 text-stone-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search entities"
                className="w-full bg-transparent text-sm outline-none"
              />
            </label>
            <label className="flex items-center gap-2 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2">
              <Filter className="h-4 w-4 text-stone-500" />
              <select value={selectedType} onChange={(event) => setSelectedType(event.target.value)} className="bg-transparent text-sm outline-none">
                <option>All</option>
                <option>Mission</option>
                <option>Goal</option>
                <option>Project</option>
                <option>Task</option>
                <option>Memory</option>
              </select>
            </label>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <div className="flex items-center gap-2">
              <Waypoints className="h-5 w-5 text-stone-700" />
              <h2 className="text-xl font-semibold">Graph nodes</h2>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              {filteredEntities.map((entity) => (
                <div key={entity.id} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-stone-500">{entity.type}</p>
                  <p className="mt-2 font-medium">{entity.title}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Relationship paths</h2>
            <div className="mt-5 space-y-3">
              {relationships.map((relationship) => (
                <div key={`${relationship.source}-${relationship.target}`} className="rounded-xl border border-stone-200 bg-stone-50 p-4 text-sm">
                  <p className="font-medium">{relationship.source} → {relationship.target}</p>
                  <p className="mt-2 text-stone-600">Type: {relationship.type}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

"use client";

import { useMemo, useState } from "react";
import { Search, Bot, Activity, ShieldCheck, ArrowRight } from "lucide-react";

const agents = [
  {
    id: "agent-launch",
    name: "Launch Agent",
    objective: "Prepare the next beta launch without over-scoping.",
    currentStep: "Review milestones and dependencies",
    status: "Executing",
    confidence: 0.87,
    health: "Healthy",
    lastActivity: "10 min ago",
    upcomingActions: ["Draft summary", "Schedule review", "Create tasks"],
  },
  {
    id: "agent-growth",
    name: "Growth Agent",
    objective: "Improve weekly reflection rituals and follow-through.",
    currentStep: "Monitor momentum and interruption patterns",
    status: "Monitoring",
    confidence: 0.74,
    health: "Needs attention",
    lastActivity: "35 min ago",
    upcomingActions: ["Recommend a shorter review ritual", "Surface blockers"],
  },
];

export default function AgentsPage() {
  const [query, setQuery] = useState("");
  const filteredAgents = useMemo(() => {
    if (!query.trim()) return agents;
    const q = query.toLowerCase();
    return agents.filter((agent) => [agent.name, agent.objective, agent.currentStep, agent.status].join(" ").toLowerCase().includes(q));
  }, [query]);

  return (
    <main className="min-h-screen bg-stone-50 p-6 text-stone-900">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <header className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="rounded-xl bg-stone-900 p-2 text-white">
                <Bot className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Agent Runtime</p>
                <h1 className="text-3xl font-semibold">Persistent agents working toward long-term goals</h1>
              </div>
            </div>
            <div className="flex items-center gap-2 rounded-2xl border border-stone-200 bg-stone-50 px-3 py-2">
              <Search className="h-4 w-4 text-stone-500" />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search agents"
                className="w-64 bg-transparent text-sm outline-none"
              />
            </div>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Agent overview</h2>
            <div className="mt-4 space-y-3">
              {filteredAgents.map((agent) => (
                <div key={agent.id} className="rounded-xl border border-stone-200 bg-stone-50 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-medium">{agent.name}</p>
                      <p className="mt-1 text-sm text-stone-600">{agent.objective}</p>
                    </div>
                    <div className="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-700">{agent.status}</div>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-stone-500">
                    <span className="rounded-full border border-stone-200 bg-white px-2.5 py-1">Confidence {Math.round(agent.confidence * 100)}%</span>
                    <span className="rounded-full border border-stone-200 bg-white px-2.5 py-1">Health {agent.health}</span>
                    <span className="rounded-full border border-stone-200 bg-white px-2.5 py-1">Last activity {agent.lastActivity}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            {filteredAgents.map((agent) => (
              <div key={agent.id} className="rounded-2xl border border-stone-200 bg-white p-6 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-medium uppercase tracking-[0.2em] text-stone-500">Active agent</p>
                    <h2 className="mt-1 text-xl font-semibold">{agent.name}</h2>
                  </div>
                  <div className="rounded-full border border-stone-200 bg-stone-50 px-3 py-1 text-sm text-stone-600">{agent.health}</div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <p className="text-sm font-semibold">Current objective</p>
                    <p className="mt-2 text-sm text-stone-600">{agent.objective}</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <p className="text-sm font-semibold">Current step</p>
                    <p className="mt-2 text-sm text-stone-600">{agent.currentStep}</p>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <div className="flex items-center gap-2">
                      <Activity className="h-4 w-4 text-stone-500" />
                      <p className="text-sm font-semibold">Confidence</p>
                    </div>
                    <p className="mt-2 text-sm text-stone-600">{Math.round(agent.confidence * 100)}% confidence in the current path.</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-stone-50 p-4">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-stone-500" />
                      <p className="text-sm font-semibold">Upcoming actions</p>
                    </div>
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-stone-600">
                      {agent.upcomingActions.map((action) => <li key={action}>{action}</li>)}
                    </ul>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between rounded-2xl border border-stone-200 bg-stone-50 p-4">
                  <span className="text-sm text-stone-600">Last activity: {agent.lastActivity}</span>
                  <button className="flex items-center gap-2 text-sm font-medium text-stone-700">
                    Review plan <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}

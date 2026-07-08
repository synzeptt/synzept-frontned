import { Clock3, Rocket, Target } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Mission } from "@/lib/types";

export function MissionHeader({ mission }: { mission: Mission }) {
  return (
    <section className="rounded-3xl border border-border bg-white p-6 shadow-soft">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="accent">Mission</Badge>
            <Badge variant={mission.status === "Completed" ? "muted" : "default"}>{mission.status}</Badge>
            <Badge variant="default">Priority: {mission.priority}</Badge>
          </div>
          <div className="space-y-2">
            <p className="text-3xl font-semibold tracking-tight text-stone-950">{mission.title}</p>
            <p className="max-w-3xl text-sm leading-6 text-stone-600">{mission.description}</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl bg-stone-950 px-4 py-3 text-white shadow-soft">
            <p className="text-xs uppercase tracking-[0.24em] text-stone-400">Health score</p>
            <p className="mt-2 text-3xl font-semibold">{mission.healthScore}%</p>
            <p className="mt-1 text-sm text-stone-300">How resilient this mission is right now.</p>
          </div>
          <div className="rounded-2xl bg-white px-4 py-3 ring-1 ring-border">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Momentum score</p>
            <p className="mt-2 text-3xl font-semibold text-stone-950">{mission.momentumScore}%</p>
            <p className="mt-1 text-sm text-stone-600">Fresh activity and forward movement.</p>
          </div>
        </div>
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-border bg-stone-50 p-4">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Start</p>
          <p className="mt-2 text-sm font-medium text-stone-950">{mission.startDate}</p>
        </div>
        <div className="rounded-2xl border border-border bg-stone-50 p-4">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Target</p>
          <p className="mt-2 text-sm font-medium text-stone-950">{mission.targetDate}</p>
        </div>
        <div className="rounded-2xl border border-border bg-stone-50 p-4">
          <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Progress</p>
          <p className="mt-2 text-sm font-medium text-stone-950">{mission.progress}% complete</p>
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-stone-600">
        <div className="inline-flex items-center gap-2 rounded-full bg-stone-100 px-3 py-2">
          <Rocket className="h-4 w-4" />
          Long-term outcome anchor
        </div>
        <div className="inline-flex items-center gap-2 rounded-full bg-stone-100 px-3 py-2">
          <Target className="h-4 w-4" />
          Connected to goals, projects, and recommendations
        </div>
        <div className="inline-flex items-center gap-2 rounded-full bg-stone-100 px-3 py-2">
          <Clock3 className="h-4 w-4" />
          Continuously updated from Memory, Reasoning, and Graph signals
        </div>
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <Button size="sm">Review mission priorities</Button>
        <Button variant="ghost" size="sm">
          Share mission briefing
        </Button>
      </div>
    </section>
  );
}

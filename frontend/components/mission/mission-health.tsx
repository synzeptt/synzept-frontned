import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Mission } from "@/lib/types";

export function MissionHealth({ mission }: { mission: Mission }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-base font-semibold text-stone-950">Health & Momentum</h2>
        <p className="text-sm text-muted-foreground">Signals from recent activity and context.</p>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-2xl bg-stone-50 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Health</p>
            <p className="mt-2 text-3xl font-semibold text-stone-950">{mission.healthScore}%</p>
            <p className="mt-1 text-sm text-stone-600">Resilience based on open loops, progress, and project alignment.</p>
          </div>
          <div className="rounded-2xl bg-stone-50 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Momentum</p>
            <p className="mt-2 text-3xl font-semibold text-stone-950">{mission.momentumScore}%</p>
            <p className="mt-1 text-sm text-stone-600">Forward movement from recent tasks, decisions, and updates.</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

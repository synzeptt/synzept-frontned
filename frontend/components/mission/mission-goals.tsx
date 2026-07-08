import { Target } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { MissionGoal } from "@/lib/types";

export function MissionGoals({ goals }: { goals: MissionGoal[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Target className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold text-stone-950">Mission goals</h2>
        </div>
        <p className="text-sm text-muted-foreground">Goal outcomes that move the mission forward.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-4">
          {goals.map((goal) => (
            <div key={goal.id} className="rounded-2xl border border-border bg-stone-50 p-4">
              <p className="text-sm font-semibold text-stone-950">{goal.title}</p>
              <p className="mt-1 text-sm text-stone-600">{goal.description}</p>
              <p className="mt-3 text-xs uppercase tracking-[0.24em] text-muted-foreground">Status: {goal.status}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

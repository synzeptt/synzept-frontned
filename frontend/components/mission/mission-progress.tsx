import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { Mission } from "@/lib/types";

export function MissionProgress({ mission }: { mission: Mission }) {
  return (
    <Card>
      <CardHeader>
        <h2 className="text-base font-semibold text-stone-950">Progress</h2>
        <p className="text-sm text-muted-foreground">Where this mission stands today.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-stone-950">Mission completion</p>
            <p className="text-sm text-muted-foreground">{mission.progress}% complete</p>
          </div>
          <p className="text-lg font-semibold text-stone-950">{mission.progress}%</p>
        </div>
        <Progress value={mission.progress} className="h-3 rounded-full" />
      </CardContent>
    </Card>
  );
}

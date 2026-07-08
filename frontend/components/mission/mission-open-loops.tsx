import { AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { MissionOpenLoop } from "@/lib/types";

export function MissionOpenLoops({ loops }: { loops: MissionOpenLoop[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold text-stone-950">Open loops</h2>
        </div>
        <p className="text-sm text-muted-foreground">Unresolved work that needs mission continuity.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {loops.map((loop) => (
          <div key={loop.id} className="rounded-2xl border border-border bg-stone-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-stone-950">{loop.title}</p>
              <span className="rounded-full bg-white px-2 py-1 text-xs text-stone-600 ring-1 ring-border">{loop.priority}</span>
            </div>
            <p className="mt-2 text-sm text-stone-600">{loop.description}</p>
            <p className="mt-3 text-xs uppercase tracking-[0.24em] text-muted-foreground">Project: {loop.projectName}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

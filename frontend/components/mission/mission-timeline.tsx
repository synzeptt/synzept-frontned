import { Clock3 } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { MissionTimelineItem } from "@/lib/types";

export function MissionTimeline({ timeline }: { timeline: MissionTimelineItem[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Clock3 className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold text-stone-950">Recent milestones</h2>
        </div>
        <p className="text-sm text-muted-foreground">Recent progress and upcoming mission events.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {timeline.map((item) => (
          <div key={item.id} className="rounded-2xl bg-stone-50 p-4">
            <p className="text-sm font-semibold text-stone-950">{item.title}</p>
            <p className="mt-1 text-sm text-stone-600">{item.detail}</p>
            <p className="mt-3 text-xs uppercase tracking-[0.22em] text-muted-foreground">{item.date}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

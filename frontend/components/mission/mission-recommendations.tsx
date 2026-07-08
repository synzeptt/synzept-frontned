import { Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { MissionRecommendation } from "@/lib/types";

export function MissionRecommendations({ recommendations }: { recommendations: MissionRecommendation[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold text-stone-950">AI recommendations</h2>
        </div>
        <p className="text-sm text-muted-foreground">Suggested next moves for this mission.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {recommendations.map((item) => (
          <div key={item.id} className="rounded-2xl border border-border bg-stone-50 p-4">
            <p className="text-sm font-semibold text-stone-950">{item.title}</p>
            <p className="mt-1 text-sm text-stone-600">{item.detail}</p>
            <p className="mt-3 text-xs uppercase tracking-[0.24em] text-muted-foreground">Source: {item.source}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

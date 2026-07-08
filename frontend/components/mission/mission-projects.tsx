import { Briefcase } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { MissionProject } from "@/lib/types";

export function MissionProjects({ projects }: { projects: MissionProject[] }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Briefcase className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-base font-semibold text-stone-950">Related projects</h2>
        </div>
        <p className="text-sm text-muted-foreground">Projects aligned to this mission.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {projects.map((project) => (
          <div key={project.id} className="rounded-2xl border border-border bg-stone-50 p-4">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-stone-950">{project.name}</p>
                <p className="mt-1 text-sm text-stone-600">{project.description}</p>
              </div>
              <Badge variant={project.status === "active" ? "accent" : "muted"}>{project.status}</Badge>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-stone-600">
              <span className="rounded-full bg-white px-2 py-1 ring-1 ring-border">Focus: {project.currentFocus}</span>
              <span className="rounded-full bg-white px-2 py-1 ring-1 ring-border">Next step: {project.recommendedNextStep}</span>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

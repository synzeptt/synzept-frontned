"use client";

import Link from "next/link";
import { ArrowRight, Plus, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspaceStore } from "@/stores/workspace-store";

export default function DashboardPage() {
  const projects = useWorkspaceStore((s) => s.projects);
  const tasks = useWorkspaceStore((s) => s.tasks);
  const activity = useWorkspaceStore((s) => s.activity);
  const memories = useWorkspaceStore((s) => s.memories);
  const createTask = useWorkspaceStore((s) => s.createTask);
  const createProject = useWorkspaceStore((s) => s.createProject);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <section className="surface p-6">
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-xs font-medium uppercase tracking-widest text-primary">Dashboard</p>
            <h2 className="mt-2 text-2xl font-semibold">Welcome back</h2>
            <p className="mt-1 text-sm text-muted-foreground">Your AI workspace overview and quick actions.</p>
          </div>
          <Button variant="primary" onClick={() => createTask("Review priorities and plan next execution.")}>
            <Sparkles size={16} />
            Plan next move
          </Button>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Stat label="Projects" value={projects.length} />
          <Stat label="Tasks" value={tasks.length} />
          <Stat label="Memories" value={memories.length} />
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="surface p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="font-semibold">Projects</h3>
            <Link href="/app/projects">
              <Button variant="ghost" size="sm">
                View all
              </Button>
            </Link>
          </div>
          <div className="space-y-3">
            {projects.slice(0, 4).map((p) => (
              <div key={p.id} className="rounded-lg border border-border/60 bg-secondary/30 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-medium">{p.name}</span>
                  <Badge variant="success">{p.status}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{p.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="surface p-5">
          <h3 className="mb-4 font-semibold">Live activity</h3>
          <div className="space-y-3">
            {activity.length === 0 ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              activity.slice(0, 5).map((e) => (
                <div key={e.id} className="border-l-2 border-primary/40 pl-3">
                  <p className="text-sm font-medium">{e.title}</p>
                  <p className="text-xs text-muted-foreground">{e.detail}</p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      <section className="surface p-5">
        <h3 className="mb-4 font-semibold">Quick actions</h3>
        <div className="grid gap-3 sm:grid-cols-3">
          <Button variant="outline" className="h-auto flex-col items-start gap-2 p-4" onClick={() => createProject()}>
            <Plus size={16} />
            New project
          </Button>
          <Link href="/app/chat">
            <Button variant="outline" className="h-auto w-full flex-col items-start gap-2 p-4">
              <Sparkles size={16} />
              Open chat
              <ArrowRight size={14} className="ml-auto" />
            </Button>
          </Link>
          <Link href="/app/workflows">
            <Button variant="outline" className="h-auto w-full flex-col items-start gap-2 p-4">
              Run workflow
              <ArrowRight size={14} className="ml-auto" />
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border/60 bg-secondary/30 p-4">
      <div className="text-2xl font-semibold tabular-nums">{value}</div>
      <div className="text-sm text-muted-foreground">{label}</div>
    </div>
  );
}

"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, MessageSquare, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { GuidanceCard } from "@/components/ui/guidance-card";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Project } from "@/lib/api";
import { useChatStore } from "@/stores/chat";
import { PageFrame } from "@frontend/components/layout/page-frame";

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const setActiveProject = useChatStore().setActiveProject;

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .listProjects()
      .then(setProjects)
      .catch(() => setError("Projects could not load. Your workspace is still safe; retry when the connection settles."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    setError(null);
    try {
      await api.createProject({ name: name.trim(), description: description.trim() || undefined });
      setName("");
      setDescription("");
      load();
    } catch {
      setError("Project could not be saved. Keep the name here and try again.");
    }
  };

  return (
    <PageFrame eyebrow="Continuity anchors" title="Projects">
      <div className="mx-auto grid max-w-6xl gap-6 p-5 md:grid-cols-[360px_1fr] md:p-7">
        <form onSubmit={create} className="h-fit rounded-xl border border-border bg-white p-4 shadow-soft">
          <p className="text-sm font-medium text-stone-950">New project</p>
          <p className="mb-3 mt-1 text-xs leading-5 text-muted-foreground">
            Give Synzept one place to hold context for work you will return to.
          </p>
          <div className="space-y-3">
            <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Project name" />
            <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Short context" />
            <Button type="submit" size="sm">
              <Plus className="mr-1.5 h-4 w-4" />
              Create
            </Button>
          </div>
          <GuidanceCard title="When to use a project" className="mt-4">
            Create one for work that will take more than one sitting. Synzept will use it to reconnect tasks, notes, threads, and memory.
          </GuidanceCard>
        </form>

        <div className="space-y-3">
          <RecoveryBanner message={error} onRetry={load} />
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-28 rounded-md" />
              <Skeleton className="h-28 rounded-md" />
            </div>
          ) : (
          <div className="grid gap-3">
            {projects.map((project) => (
              <article key={project.id} className="rounded-xl border border-border bg-white p-4 shadow-soft transition duration-150 hover:-translate-y-0.5 hover:bg-stone-50">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h2 className="truncate text-base font-medium text-stone-950">{project.name}</h2>
                    <p className="mt-1 line-clamp-2 text-sm leading-6 text-muted-foreground">{project.context_summary || project.description || "Context will collect here as you work."}</p>
                  </div>
                  <Link href={`/projects/${project.id}`} className="grid h-9 w-9 shrink-0 place-items-center rounded-md text-stone-600 hover:bg-stone-50 hover:text-stone-950" aria-label={`Open ${project.name}`}>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
                <div className="mt-4 flex gap-2">
                  <Link href="/chat" onClick={() => setActiveProject(project.id)}>
                    <Button variant="outline" size="sm">
                      <MessageSquare className="mr-1.5 h-4 w-4" />
                      Continue
                    </Button>
                  </Link>
                </div>
              </article>
            ))}
            {!projects.length && (
              <EmptyState
                icon={<Plus className="h-5 w-5" />}
                title="Create your first continuity anchor"
                description="Projects give Synzept a stable place to connect notes, tasks, conversations, and memory around work you care about."
                steps={[
                  "Use a project for an ongoing area of work, not every tiny task.",
                  "Add one short context line so Synzept knows why it matters.",
                  "Continue from the project whenever you want related context restored.",
                ]}
                action={
                  <Button type="button" variant="outline" size="sm" onClick={() => document.querySelector<HTMLInputElement>('input[placeholder="Project name"]')?.focus()}>
                    Focus project name
                  </Button>
                }
              />
            )}
          </div>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

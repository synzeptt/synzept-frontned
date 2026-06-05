"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Project } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [currentFocus, setCurrentFocus] = useState("");
  const [recommendedNextStep, setRecommendedNextStep] = useState("");
  const [error, setError] = useState<string | null>(null);

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
      await api.createProject({
        name: name.trim(),
        description: description.trim(),
        currentFocus: currentFocus.trim(),
        recommendedNextStep: recommendedNextStep.trim(),
      });
      setName("");
      setDescription("");
      setCurrentFocus("");
      setRecommendedNextStep("");
      load();
    } catch {
      setError("Project could not be saved. Keep the details here and try again.");
    }
  };

  return (
    <PageFrame eyebrow="Project Intelligence" title="Projects">
      <div className="mx-auto grid max-w-6xl gap-6 p-5 md:grid-cols-[360px_1fr] md:p-7">
        <form onSubmit={create} className="h-fit rounded-lg border border-border bg-white p-4 shadow-soft">
          <p className="text-sm font-medium text-stone-950">New project</p>
          <p className="mb-3 mt-1 text-xs leading-5 text-muted-foreground">
            Give Synzept enough context to answer what matters next.
          </p>
          <div className="space-y-3">
            <Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Project name" />
            <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Short description" />
            <textarea
              value={currentFocus}
              onChange={(event) => setCurrentFocus(event.target.value)}
              placeholder="Current focus"
              className="min-h-20 w-full resize-y rounded-lg border border-border bg-white px-3.5 py-2 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
            />
            <textarea
              value={recommendedNextStep}
              onChange={(event) => setRecommendedNextStep(event.target.value)}
              placeholder="Recommended next step"
              className="min-h-20 w-full resize-y rounded-lg border border-border bg-white px-3.5 py-2 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
            />
            <Button type="submit" size="sm">
              <Plus className="mr-1.5 h-4 w-4" />
              Create
            </Button>
          </div>
        </form>

        <div className="space-y-3">
          <RecoveryBanner message={error} onRetry={load} />
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-32 rounded-md" />
              <Skeleton className="h-32 rounded-md" />
            </div>
          ) : (
            <div className="grid gap-3">
              {projects.map((project) => (
                <article key={project.id} className="rounded-lg border border-border bg-white p-4 shadow-soft">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <h2 className="truncate text-base font-medium text-stone-950">{project.name}</h2>
                      <p className="mt-1 line-clamp-2 text-sm leading-6 text-muted-foreground">{project.description || "No description yet."}</p>
                    </div>
                    <Link href={`/projects/${project.id}`} className="grid h-9 w-9 shrink-0 place-items-center rounded-md text-stone-600 hover:bg-stone-50 hover:text-stone-950" aria-label={`Open ${project.name}`}>
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <ProjectSignal label="Current Focus" value={project.currentFocus} empty="Set the current focus for this project." />
                    <ProjectSignal label="Recommended Next Step" value={project.recommendedNextStep} empty="Define the next action to keep momentum." />
                  </div>
                </article>
              ))}
              {!projects.length && (
                <EmptyState
                  icon={<Plus className="h-5 w-5" />}
                  title="Create your first project"
                  description="Every project becomes a continuity anchor with focus, unfinished loops, decisions, and a next step."
                  steps={[
                    "Name the project.",
                    "Set the current focus.",
                    "Define the next action so momentum is visible when you return.",
                  ]}
                />
              )}
            </div>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

function ProjectSignal({ label, value, empty }: { label: string; value?: string; empty: string }) {
  return (
    <div className="rounded-md border border-border bg-stone-50 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className="mt-1 text-sm leading-5 text-stone-700">{value || <span className="text-stone-400">{empty}</span>}</p>
    </div>
  );
}

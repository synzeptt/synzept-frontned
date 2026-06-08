"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus, Search, Target } from "lucide-react";
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
  const [search, setSearch] = useState("");
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

  const activeProjects = useMemo(() => projects.filter((project) => project.status !== "archived" && project.status !== "completed"), [projects]);
  const projectsWithFocus = useMemo(() => projects.filter((project) => Boolean(project.currentFocus?.trim())), [projects]);
  const projectsWithNextStep = useMemo(() => projects.filter((project) => Boolean(project.recommendedNextStep?.trim())), [projects]);
  const needsContinuity = useMemo(
    () => activeProjects.filter((project) => !project.currentFocus?.trim() || !project.recommendedNextStep?.trim()),
    [activeProjects],
  );
  const resumeProject = useMemo(
    () =>
      activeProjects
        .slice()
        .sort((a, b) => {
          const aReady = Number(Boolean(a.currentFocus?.trim()) && Boolean(a.recommendedNextStep?.trim()));
          const bReady = Number(Boolean(b.currentFocus?.trim()) && Boolean(b.recommendedNextStep?.trim()));
          if (aReady !== bReady) return bReady - aReady;
          return projectTimestamp(b).localeCompare(projectTimestamp(a));
        })[0],
    [activeProjects],
  );
  const visibleProjects = useMemo(() => {
    const query = search.trim().toLowerCase();
    const sorted = projects.slice().sort((a, b) => {
      const aReady = Number(Boolean(a.currentFocus?.trim()) && Boolean(a.recommendedNextStep?.trim()));
      const bReady = Number(Boolean(b.currentFocus?.trim()) && Boolean(b.recommendedNextStep?.trim()));
      if (aReady !== bReady) return bReady - aReady;
      return (b.updatedAt || b.createdAt || b.created_at || "").localeCompare(a.updatedAt || a.createdAt || a.created_at || "");
    });
    if (!query) return sorted;
    return sorted.filter((project) =>
      [project.name, project.description, project.currentFocus, project.recommendedNextStep, project.context_summary]
        .some((value) => value?.toLowerCase().includes(query)),
    );
  }, [projects, search]);

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
          <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
              <div className="min-w-0">
                <p className="text-xs font-medium uppercase text-stone-400">Project mission control</p>
                <h2 className="mt-2 line-clamp-2 text-xl font-semibold leading-7">
                  {resumeProject?.currentFocus || resumeProject?.name || "Create one project anchor."}
                </h2>
                <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-300">
                  {resumeProject?.recommendedNextStep ||
                    resumeProject?.description ||
                    "A project becomes useful when it has a current focus and one visible next step."}
                </p>
              </div>
              <div className="flex flex-col gap-2 lg:w-44">
                <Link
                  href={resumeProject ? `/projects/${resumeProject.id}` : "/projects"}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-stone-950 transition hover:bg-stone-100"
                >
                  {resumeProject ? "Resume project" : "Start here"}
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <p className="text-xs leading-5 text-stone-400">
                  {resumeProject ? `Last changed ${formatProjectDate(projectTimestamp(resumeProject))}.` : "Set the focus and next step first."}
                </p>
              </div>
            </div>
          </section>
          <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="flex items-center gap-2 text-sm font-medium text-stone-950">
                  <Target className="h-4 w-4 text-muted-foreground" />
                  Continuity anchors
                </p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">
                  Projects are strongest when both current focus and next step are visible.
                </p>
              </div>
              <span className="rounded-md bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{activeProjects.length} active</span>
            </div>
            <div className="mt-4 grid gap-2 sm:grid-cols-3">
              <ProjectMetric label="With focus" value={projectsWithFocus.length} total={projects.length} />
              <ProjectMetric label="With next step" value={projectsWithNextStep.length} total={projects.length} />
              <ProjectMetric label="Need attention" value={needsContinuity.length} total={activeProjects.length} />
            </div>
            {!!needsContinuity.length && (
              <div className="mt-4 space-y-2">
                {needsContinuity.slice(0, 3).map((project) => (
                  <Link key={project.id} href={`/projects/${project.id}`} className="flex items-center justify-between gap-3 rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-700 transition hover:bg-stone-100">
                    <span className="truncate">{project.name}</span>
                    <span className="shrink-0 text-xs text-stone-500">{!project.currentFocus?.trim() ? "Add focus" : "Add next step"}</span>
                  </Link>
                ))}
              </div>
            )}
          </section>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Find projects by name, focus, or next step" className="pl-9" />
          </div>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-32 rounded-md" />
              <Skeleton className="h-32 rounded-md" />
            </div>
          ) : (
            <div className="grid gap-3">
              {visibleProjects.map((project) => (
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
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="rounded-md bg-stone-50 px-2 py-1">{project.status || "active"}</span>
                    <span className="rounded-md bg-stone-50 px-2 py-1">Updated {formatProjectDate(projectTimestamp(project))}</span>
                    {!project.currentFocus?.trim() && <span className="rounded-md bg-amber-50 px-2 py-1 text-amber-800">Needs focus</span>}
                    {!project.recommendedNextStep?.trim() && <span className="rounded-md bg-amber-50 px-2 py-1 text-amber-800">Needs next step</span>}
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
              {!!projects.length && !visibleProjects.length && (
                <EmptyState
                  icon={<Search className="h-5 w-5" />}
                  title="No matching projects"
                  description="Try a project name, current focus, recommended next step, or saved context phrase."
                />
              )}
            </div>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

function ProjectMetric({ label, value, total }: { label: string; value: number; total: number }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-2">
      <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-stone-950">
        {value}
        <span className="ml-1 text-xs font-normal text-muted-foreground">/ {total || 0}</span>
      </p>
    </div>
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

function projectTimestamp(project: Project) {
  return project.updatedAt || project.createdAt || project.created_at || "";
}

function formatProjectDate(value: string) {
  if (!value) return "recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

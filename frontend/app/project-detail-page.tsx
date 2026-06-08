"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Archive, ArrowRight, Check, Plus, Save, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Decision, type OpenLoop, type Project } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

export function ProjectDetailPage({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [openLoops, setOpenLoops] = useState<OpenLoop[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", description: "", currentFocus: "", recommendedNextStep: "", status: "active" });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([api.getProject(projectId), api.listOpenLoops(projectId), api.listDecisions(projectId)])
      .then(([projectData, loopsData, decisionsData]) => {
        setProject(projectData);
        setOpenLoops(loopsData);
        setDecisions(decisionsData);
        setDraft({
          name: projectData.name,
          description: projectData.description || "",
          currentFocus: projectData.currentFocus || "",
          recommendedNextStep: projectData.recommendedNextStep || "",
          status: projectData.status,
        });
      })
      .catch(() => setError("Project intelligence could not load. Retry when the connection settles."))
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const recentActivity = useMemo(() => {
    const items = [
      ...(project ? [{ id: project.id, title: "Project updated", detail: project.name, at: project.updatedAt || project.createdAt || "" }] : []),
      ...openLoops.map((item) => ({ id: item.id, title: item.status === "completed" ? "Open loop completed" : "Open loop updated", detail: item.title, at: item.updatedAt })),
      ...decisions.map((item) => ({ id: item.id, title: item.status === "decided" ? "Decision made" : "Decision pending", detail: item.title, at: item.updatedAt })),
    ];
    return items.sort((a, b) => String(b.at).localeCompare(String(a.at))).slice(0, 6);
  }, [decisions, openLoops, project]);
  const openLoopCount = openLoops.filter((item) => item.status === "open").length;
  const pendingDecisionCount = decisions.filter((item) => item.status === "pending").length;
  const completedLoopCount = openLoops.filter((item) => item.status === "completed").length;
  const continuityScore = getProjectContinuityScore({
    hasFocus: Boolean(draft.currentFocus.trim()),
    hasNextStep: Boolean(draft.recommendedNextStep.trim()),
    hasRecentActivity: recentActivity.length > 0,
    closedLoops: completedLoopCount,
    totalLoops: openLoops.length,
  });

  const saveProject = async () => {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateProject(projectId, draft);
      setProject(updated);
      setDraft({
        name: updated.name,
        description: updated.description || "",
        currentFocus: updated.currentFocus || "",
        recommendedNextStep: updated.recommendedNextStep || "",
        status: updated.status,
      });
    } catch {
      setError("Project could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const archiveProject = async () => {
    await api.deleteProject(projectId);
    setDraft((current) => ({ ...current, status: "archived" }));
  };

  if (loading) {
    return (
      <PageFrame eyebrow="Project Intelligence" title="Project">
        <div className="mx-auto max-w-6xl p-5 md:p-7">
          <Skeleton className="h-48 rounded-md" />
        </div>
      </PageFrame>
    );
  }

  return (
    <PageFrame
      eyebrow="Project Intelligence"
      title={project?.name || "Project"}
      action={
        <Button size="sm" variant="ghost" onClick={archiveProject}>
          <Archive className="mr-1.5 h-4 w-4" />
          Archive
        </Button>
      }
    >
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />

        <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase text-stone-400">Project continuity</p>
              <h2 className="mt-2 line-clamp-2 text-2xl font-semibold leading-8">
                {draft.currentFocus || "Set the current focus for this project."}
              </h2>
              <p className="mt-3 line-clamp-3 text-sm leading-6 text-stone-300">
                {draft.recommendedNextStep || "Define the next step so this project has a clear return point."}
              </p>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <ProjectSnapshotStat label="Open loops" value={openLoopCount} />
                <ProjectSnapshotStat label="Pending decisions" value={pendingDecisionCount} />
                <ProjectSnapshotStat label="Changes" value={recentActivity.length} />
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs font-medium uppercase text-stone-400">Progress visibility</p>
              <p className="mt-2 text-3xl font-semibold">{continuityScore}%</p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-white" style={{ width: `${continuityScore}%` }} />
              </div>
              <p className="mt-3 text-sm leading-6 text-stone-300">
                {openLoopCount || pendingDecisionCount
                  ? "Finish one loop or decision to make the next return cleaner."
                  : "The project has no tracked unfinished loops right now."}
              </p>
              <button
                type="button"
                onClick={saveProject}
                disabled={saving}
                className="mt-4 inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-3 text-sm font-medium text-stone-950 transition hover:bg-stone-100 disabled:opacity-60"
              >
                {saving ? "Saving..." : "Save continuity"}
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-stone-950">Project profile</p>
              <p className="mt-1 text-xs text-muted">This answers what you are working on and what should happen next.</p>
            </div>
            <Button size="sm" onClick={saveProject} disabled={saving}>
              <Save className="mr-1.5 h-4 w-4" />
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="Project name" />
            <select
              value={draft.status}
              onChange={(event) => setDraft({ ...draft, status: event.target.value })}
              className="h-10 rounded-lg border border-border bg-white px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
            >
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
            <textarea className="min-h-24 rounded-lg border border-border bg-white px-3 py-2 text-sm outline-none md:col-span-2" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} placeholder="Description" />
            <IntelligenceTextarea label="Current Focus" value={draft.currentFocus} empty="Set the current focus for this project." onChange={(value) => setDraft({ ...draft, currentFocus: value })} />
            <IntelligenceTextarea label="Recommended Next Step" value={draft.recommendedNextStep} empty="Define the next action to keep momentum." onChange={(value) => setDraft({ ...draft, recommendedNextStep: value })} />
          </div>
        </section>

        <div className="grid gap-5 lg:grid-cols-2">
          <OpenLoopPanel projectId={projectId} items={openLoops} setItems={setOpenLoops} setError={setError} />
          <DecisionPanel projectId={projectId} items={decisions} setItems={setDecisions} setError={setError} />
        </div>

        <section className="rounded-lg border border-border bg-white p-5">
          <p className="text-sm font-medium text-stone-950">What Changed</p>
          <div className="mt-3 space-y-2">
            {recentActivity.map((item) => (
              <div key={`${item.title}-${item.id}`} className="rounded-md bg-stone-50 px-3 py-2">
                <p className="text-sm text-stone-800">{item.title}</p>
                <p className="mt-0.5 text-xs text-muted">{item.detail}</p>
              </div>
            ))}
            {!recentActivity.length && <p className="text-sm text-muted">No meaningful project changes have been captured yet.</p>}
          </div>
        </section>
      </div>
    </PageFrame>
  );
}

function ProjectSnapshotStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-white/5 px-3 py-3">
      <p className="text-2xl font-semibold text-white">{value}</p>
      <p className="mt-1 text-xs text-stone-400">{label}</p>
    </div>
  );
}

function getProjectContinuityScore({
  hasFocus,
  hasNextStep,
  hasRecentActivity,
  closedLoops,
  totalLoops,
}: {
  hasFocus: boolean;
  hasNextStep: boolean;
  hasRecentActivity: boolean;
  closedLoops: number;
  totalLoops: number;
}) {
  const loopScore = totalLoops ? Math.round((closedLoops / totalLoops) * 25) : 15;
  return Math.min(100, (hasFocus ? 25 : 0) + (hasNextStep ? 30 : 0) + (hasRecentActivity ? 20 : 0) + loopScore);
}

function IntelligenceTextarea({ label, value, empty, onChange }: { label: string; value: string; empty: string; onChange: (value: string) => void }) {
  return (
    <div>
      <label className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{label}</label>
      {!value.trim() && <p className="mt-1 text-sm text-stone-400">{empty}</p>}
      <textarea className="mt-2 min-h-28 w-full resize-y rounded-lg border border-border bg-white px-3 py-2 text-sm outline-none" value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

function OpenLoopPanel({ projectId, items, setItems, setError }: { projectId: string; items: OpenLoop[]; setItems: (items: OpenLoop[]) => void; setError: (value: string | null) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const add = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    try {
      const item = await api.createOpenLoop(projectId, { title: title.trim(), description: description.trim() });
      setItems([item, ...items]);
      setTitle("");
      setDescription("");
    } catch {
      setError("Open loop could not be saved.");
    }
  };

  const update = async (item: OpenLoop, status: OpenLoop["status"]) => {
    const updated = await api.updateOpenLoop(item.id, { status });
    setItems(items.map((candidate) => (candidate.id === item.id ? updated : candidate)));
  };

  const remove = async (item: OpenLoop) => {
    await api.deleteOpenLoop(item.id);
    setItems(items.filter((candidate) => candidate.id !== item.id));
  };

  return (
    <section className="rounded-lg border border-border bg-white p-5">
      <p className="text-sm font-medium text-stone-950">Open Loops</p>
      <form onSubmit={add} className="mt-3 space-y-2">
        <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Unfinished thread" />
        <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Why it matters" />
        <Button size="sm" type="submit"><Plus className="mr-1.5 h-4 w-4" />Add Open Loop</Button>
      </form>
      <div className="mt-4 space-y-2">
        {items.map((item) => (
          <div key={item.id} className="rounded-md border border-border bg-stone-50 p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-stone-800">{item.title}</p>
                {item.description && <p className="mt-1 text-xs leading-5 text-muted">{item.description}</p>}
              </div>
              <Badge variant={item.status === "open" ? "accent" : "muted"}>{item.status}</Badge>
            </div>
            <div className="mt-3 flex gap-2">
              {item.status === "open" && <Button size="sm" variant="outline" onClick={() => update(item, "completed")}><Check className="mr-1.5 h-4 w-4" />Complete</Button>}
              <Button size="sm" variant="ghost" onClick={() => remove(item)}><Trash2 className="mr-1.5 h-4 w-4" />Delete</Button>
            </div>
          </div>
        ))}
        {!items.length && <p className="text-sm text-muted">No open loops yet.</p>}
      </div>
    </section>
  );
}

function DecisionPanel({ projectId, items, setItems, setError }: { projectId: string; items: Decision[]; setItems: (items: Decision[]) => void; setError: (value: string | null) => void }) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const add = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    try {
      const item = await api.createDecision(projectId, { title: title.trim(), description: description.trim() });
      setItems([item, ...items]);
      setTitle("");
      setDescription("");
    } catch {
      setError("Decision could not be saved.");
    }
  };

  const update = async (item: Decision, status: Decision["status"]) => {
    const updated = await api.updateDecision(item.id, { status });
    setItems(items.map((candidate) => (candidate.id === item.id ? updated : candidate)));
  };

  const remove = async (item: Decision) => {
    await api.deleteDecision(item.id);
    setItems(items.filter((candidate) => candidate.id !== item.id));
  };

  return (
    <section className="rounded-lg border border-border bg-white p-5">
      <p className="text-sm font-medium text-stone-950">Decisions</p>
      <form onSubmit={add} className="mt-3 space-y-2">
        <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Decision to track" />
        <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Decision context" />
        <Button size="sm" type="submit"><Plus className="mr-1.5 h-4 w-4" />Add Decision</Button>
      </form>
      <div className="mt-4 space-y-2">
        {items.map((item) => (
          <div key={item.id} className="rounded-md border border-border bg-stone-50 p-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-medium text-stone-800">{item.title}</p>
                {item.description && <p className="mt-1 text-xs leading-5 text-muted">{item.description}</p>}
              </div>
              <Badge variant={item.status === "decided" ? "accent" : "muted"}>{item.status}</Badge>
            </div>
            <div className="mt-3 flex gap-2">
              {item.status === "pending" && <Button size="sm" variant="outline" onClick={() => update(item, "decided")}><Check className="mr-1.5 h-4 w-4" />Mark Decided</Button>}
              <Button size="sm" variant="ghost" onClick={() => remove(item)}><Trash2 className="mr-1.5 h-4 w-4" />Delete</Button>
            </div>
          </div>
        ))}
        {!items.length && <p className="text-sm text-muted">No decisions yet.</p>}
      </div>
    </section>
  );
}

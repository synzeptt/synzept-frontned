"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, Archive, ArrowRight, Check, ClipboardCheck, HeartPulse, Lightbulb, Plus, RotateCcw, Save, Target, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProGate } from "@/components/pro/pro-gate";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Decision, type LearningSuggestion, type Note, type OpenLoop, type Project, type Task } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

const doneStatuses = new Set(["completed", "archived", "done"]);

export function ProjectDetailPage({ projectId }: { projectId: string }) {
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [openLoops, setOpenLoops] = useState<OpenLoop[]>([]);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [acceptedLearnings, setAcceptedLearnings] = useState<LearningSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ name: "", description: "", currentFocus: "", recommendedNextStep: "", status: "active" });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.getProject(projectId),
      api.listOpenLoops(projectId),
      api.listDecisions(projectId),
      api.listNotes(projectId).catch(() => []),
      api.listTasks(undefined, projectId).catch(() => []),
      api.getLearningEngine().catch(() => ({ observations: [], suggestions: [] })),
    ])
      .then(([projectData, loopsData, decisionsData, noteRows, taskRows, learning]) => {
        setProject(projectData);
        setOpenLoops(loopsData);
        setDecisions(decisionsData);
        setNotes(noteRows);
        setTasks(taskRows);
        setAcceptedLearnings(learning.suggestions.filter((item) => item.status === "accepted"));
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
      ...notes.map((item) => ({ id: item.id, title: "Note added", detail: item.title || item.summary || item.content, at: item.created_at })),
      ...tasks.map((item) => ({ id: item.id, title: item.status === "completed" || item.status === "done" ? "Task completed" : "Task updated", detail: item.title, at: item.created_at })),
    ];
    return items.sort((a, b) => String(b.at).localeCompare(String(a.at))).slice(0, 6);
  }, [decisions, notes, openLoops, project, tasks]);
  const pendingDecisionCount = decisions.filter((item) => item.status === "pending").length;
  const completedLoopCount = openLoops.filter((item) => item.status === "completed").length;
  const openTasks = tasks.filter((item) => !doneStatuses.has(item.status));
  const recentDecisions = decisions.filter((item) => item.status === "decided").slice(0, 5);
  const intelligence = useMemo(
    () => getProjectIntelligence({ project, draft, openLoops, decisions, notes, tasks, recentActivity }),
    [decisions, draft, notes, openLoops, project, recentActivity, tasks],
  );
  const continuityScore = getProjectContinuityScore({
    hasFocus: Boolean(draft.currentFocus.trim()),
    hasNextStep: Boolean(draft.recommendedNextStep.trim()),
    hasRecentActivity: recentActivity.length > 0,
    closedLoops: completedLoopCount,
    totalLoops: openLoops.length + openTasks.length + pendingDecisionCount,
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
    setError(null);
    try {
      await api.archiveProject(projectId);
      router.push("/projects");
    } catch {
      setError("Project could not be archived.");
    }
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
      <ProGate feature="Project Intelligence" description="Project Intelligence is a Synzept Pro workspace that shows current focus, open loops, recent activity, decisions, recommended next step, and project health.">
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />

        <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase text-stone-400">Project continuity</p>
              <h2 className="mt-2 line-clamp-2 text-2xl font-semibold leading-8">
                {intelligence.currentFocus}
              </h2>
              <p className="mt-3 line-clamp-3 text-sm leading-6 text-stone-300">
                {intelligence.recommendedNextStep}
              </p>
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                <ProjectSnapshotStat label="Unfinished" value={intelligence.unfinished.length} />
                <ProjectSnapshotStat label="Pending decisions" value={pendingDecisionCount} />
                <ProjectSnapshotStat label="Changes" value={recentActivity.length} />
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="text-xs font-medium uppercase text-stone-400">Project health</p>
              <p className="mt-2 text-3xl font-semibold">{intelligence.health.label}</p>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-white" style={{ width: `${continuityScore}%` }} />
              </div>
              <p className="mt-3 text-sm leading-6 text-stone-300">
                {intelligence.health.reason}
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-5">
            <IntelligencePanel
              icon={<Target className="h-4 w-4" />}
              title="Current Focus"
              question="What is the current priority?"
              empty="Set a current focus so this project has a clear return point."
            >
              <p className="text-lg font-semibold leading-7 text-stone-950">{intelligence.currentFocus}</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{intelligence.currentFocusReason}</p>
            </IntelligencePanel>

            <IntelligencePanel
              icon={<RotateCcw className="h-4 w-4" />}
              title="Open Loops"
              question="What remains unfinished?"
              empty="No unfinished work is linked to this project right now."
            >
              <div className="space-y-2">
                {intelligence.unfinished.slice(0, 8).map((item) => (
                  <ProjectIntelligenceRow key={item.id} title={item.title} detail={item.detail} meta={item.type} href={item.href} />
                ))}
                {!intelligence.unfinished.length && <EmptyLine text="No open loops, pending tasks, or unresolved decisions." />}
              </div>
            </IntelligencePanel>

            <IntelligencePanel
              icon={<Activity className="h-4 w-4" />}
              title="Recent Activity"
              question="What changed recently?"
              empty="Recent updates will appear as notes, tasks, decisions, and loops change."
            >
              <div className="space-y-2">
                {recentActivity.map((item) => (
                  <ProjectIntelligenceRow key={`${item.title}-${item.id}`} title={item.title} detail={item.detail} meta={formatShortDate(item.at)} />
                ))}
                {!recentActivity.length && <EmptyLine text="No meaningful project changes have been captured yet." />}
              </div>
            </IntelligencePanel>
          </div>

          <div className="space-y-5">
            <IntelligencePanel
              icon={<ArrowRight className="h-4 w-4" />}
              title="Recommended Next Step"
              question="What should I do next?"
              empty="Define one concrete next action."
            >
              <p className="text-lg font-semibold leading-7 text-stone-950">{intelligence.recommendedNextStep}</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{intelligence.nextStepReason}</p>
            </IntelligencePanel>

            <IntelligencePanel
              icon={<ClipboardCheck className="h-4 w-4" />}
              title="Recent Decisions"
              question="What decisions have already been made?"
              empty="Decisions you mark as decided will appear here."
            >
              <div className="space-y-2">
                {recentDecisions.map((item) => (
                  <ProjectIntelligenceRow key={item.id} title={item.title} detail={item.description || "Decision recorded."} meta={formatShortDate(item.updatedAt)} />
                ))}
                {!recentDecisions.length && <EmptyLine text="No decided project decisions yet." />}
              </div>
            </IntelligencePanel>

            <IntelligencePanel
              icon={<HeartPulse className="h-4 w-4" />}
              title="Project Health"
              question="How is this project doing?"
              empty="Project health appears after Synzept sees project signals."
            >
              <div className="rounded-md bg-stone-50 p-4">
                <p className="text-2xl font-semibold text-stone-950">{intelligence.health.label}</p>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{intelligence.health.reason}</p>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-stone-200">
                  <div className="h-full rounded-full bg-stone-900" style={{ width: `${continuityScore}%` }} />
                </div>
              </div>
            </IntelligencePanel>

            <IntelligencePanel
              icon={<Lightbulb className="h-4 w-4" />}
              title="Approved Learning Context"
              question="What user-approved context can shape this workspace?"
              empty="Accepted learnings will appear here."
            >
              <div className="space-y-2">
                {acceptedLearnings.slice(0, 3).map((item) => (
                  <ProjectIntelligenceRow key={item.id} title={item.title} detail={item.description} meta={`${Math.round((item.confidence || 0.5) * 100)}%`} />
                ))}
                {!acceptedLearnings.length && <EmptyLine text="No approved learnings yet. Review suggestions in Learning." />}
              </div>
            </IntelligencePanel>
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
      </div>
      </ProGate>
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

function IntelligencePanel({
  icon,
  title,
  question,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  question: string;
  empty: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-stone-100 text-stone-700">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold text-stone-950">{title}</p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{question}</p>
        </div>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ProjectIntelligenceRow({ title, detail, meta, href }: { title: string; detail?: string; meta?: string; href?: string }) {
  const content = (
    <>
      <div className="min-w-0">
        <p className="line-clamp-2 text-sm font-medium text-stone-900">{title}</p>
        {detail && <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{detail}</p>}
      </div>
      {meta && <span className="shrink-0 rounded-md bg-stone-100 px-2 py-1 text-[11px] text-stone-600">{meta}</span>}
    </>
  );
  if (href) {
    return (
      <Link href={href} className="flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
        {content}
      </Link>
    );
  }
  return <div className="flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-3">{content}</div>;
}

function EmptyLine({ text }: { text: string }) {
  return <p className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-muted-foreground">{text}</p>;
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

function getProjectIntelligence({
  project,
  draft,
  openLoops,
  decisions,
  notes,
  tasks,
  recentActivity,
}: {
  project: Project | null;
  draft: { name: string; description: string; currentFocus: string; recommendedNextStep: string; status: string };
  openLoops: OpenLoop[];
  decisions: Decision[];
  notes: Note[];
  tasks: Task[];
  recentActivity: Array<{ id: string; title: string; detail: string | null; at: string }>;
}) {
  const openLoopRows = openLoops
    .filter((item) => item.status === "open")
    .map((item) => ({
      id: `loop-${item.id}`,
      title: item.title,
      detail: item.description || "Tracked open loop.",
      type: "Open loop",
      href: "/open-loops",
    }));
  const taskRows = tasks
    .filter((item) => !doneStatuses.has(item.status))
    .map((item) => ({
      id: `task-${item.id}`,
      title: item.title,
      detail: item.description || (item.due_at ? `Due ${formatShortDate(item.due_at)}` : `Priority: ${item.priority}`),
      type: isBlockedTask(item) ? "Blocked" : "Task",
      href: "/tasks",
    }));
  const decisionRows = decisions
    .filter((item) => item.status === "pending")
    .map((item) => ({
      id: `decision-${item.id}`,
      title: item.title,
      detail: item.description || "Decision still pending.",
      type: "Decision",
      href: undefined,
    }));
  const unfinished = [...openLoopRows, ...decisionRows, ...taskRows];
  const latestNote = notes[0];
  const firstOpenLoop = openLoopRows[0];
  const firstDecision = decisionRows[0];
  const firstTask = taskRows[0];
  const currentFocus =
    draft.currentFocus.trim() ||
    firstOpenLoop?.title ||
    firstDecision?.title ||
    firstTask?.title ||
    draft.description.trim() ||
    `Clarify the current priority for ${draft.name || project?.name || "this project"}.`;
  const currentFocusReason =
    draft.currentFocus.trim()
      ? "This focus is saved on the project profile."
      : firstOpenLoop
        ? "Synzept inferred this from the highest visible unfinished loop."
        : firstDecision
          ? "Synzept inferred this from an unresolved decision."
          : firstTask
            ? "Synzept inferred this from an unfinished task."
            : latestNote
              ? "Synzept inferred this from recent project context."
              : "Add a focus, task, note, or loop to make this project easier to resume.";
  const recommendedNextStep =
    draft.recommendedNextStep.trim() ||
    (firstOpenLoop ? `Close the loop: ${firstOpenLoop.title}` : "") ||
    (firstDecision ? `Resolve the decision: ${firstDecision.title}` : "") ||
    (firstTask ? `Continue the task: ${firstTask.title}` : "") ||
    (latestNote ? `Turn "${latestNote.title || "the latest note"}" into a task or decision.` : "") ||
    `Define the next concrete action for ${draft.name || project?.name || "this project"}.`;
  const nextStepReason =
    draft.recommendedNextStep.trim()
      ? "This recommendation is saved on the project profile."
      : unfinished.length
        ? "This is based on the most important unfinished work in the project."
        : latestNote
          ? "This keeps recent context from becoming passive notes."
          : "A single next action makes the project resumable after days or weeks away.";
  const health = getProjectHealth({ project, draft, unfinished, decisions, recentActivity });

  return {
    currentFocus,
    currentFocusReason,
    recommendedNextStep,
    nextStepReason,
    unfinished,
    health,
  };
}

function getProjectHealth({
  project,
  draft,
  unfinished,
  decisions,
  recentActivity,
}: {
  project: Project | null;
  draft: { currentFocus: string; recommendedNextStep: string; status: string };
  unfinished: Array<{ type: string }>;
  decisions: Decision[];
  recentActivity: Array<{ at: string }>;
}) {
  if (draft.status === "completed") return { label: "Healthy", reason: "This project is marked complete." };
  if (draft.status === "paused") return { label: "Stalled", reason: "This project is paused and needs a restart decision before work continues." };
  const hasBlocked = unfinished.some((item) => item.type === "Blocked");
  if (hasBlocked) return { label: "Blocked", reason: "At least one linked task or loop is blocked." };
  const pendingDecisions = decisions.filter((item) => item.status === "pending").length;
  if (pendingDecisions || !draft.currentFocus.trim() || !draft.recommendedNextStep.trim()) {
    return { label: "Needs Attention", reason: "The project has unresolved decisions or is missing a clear focus and next step." };
  }
  const last = project?.updatedAt || project?.createdAt || recentActivity[0]?.at;
  if (last && daysSince(last) >= 7) return { label: "Stalled", reason: `No meaningful activity has been captured for ${daysSince(last)} days.` };
  if (unfinished.length) return { label: "Active", reason: "The project is moving, with visible unfinished work to continue." };
  return { label: "Healthy", reason: "The project has focus, a next step, recent movement, and no visible unfinished work." };
}

function isBlockedTask(task: Task) {
  const text = `${task.title} ${task.description || ""}`.toLowerCase();
  return text.includes("blocked") || text.includes("stuck") || text.includes("waiting");
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
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-sm font-medium text-stone-950">
            <RotateCcw className="h-4 w-4 text-muted" />
            Open Loops
          </p>
          <p className="mt-1 text-xs leading-5 text-muted">Unfinished work, blockers, follow-ups, and waiting items for this project.</p>
        </div>
        <Link href="/open-loops" className="shrink-0 rounded-md border border-border px-2 py-1 text-xs text-stone-700 transition hover:bg-stone-50">
          View all
        </Link>
      </div>
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

function formatShortDate(value?: string | null) {
  if (!value) return "recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function daysSince(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 0;
  const diff = Date.now() - date.getTime();
  return Math.max(0, Math.floor(diff / 86_400_000));
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertCircle, ArrowUpRight, Check, CheckCircle2, Clock3, Copy, History, LoaderCircle, RefreshCw, RotateCcw, Search, Sparkles, X, XCircle } from "lucide-react";
import { WorkspacePage } from "@/components/layout/workspace-content";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, clearSynzeptContextCache, type ActionExecution, type Dashboard, type ExecutionState, type MemoryExplorerItem, type MemoryTrustEvent, type Task } from "@/lib/api";
import { useWorkspaceStore } from "@/stores/workspace";

type ActionStatus = "running" | "waiting" | "completed" | "failed";
type ActionFilter = "all" | ActionStatus;

type SynzeptAction = {
  id: string;
  title: string;
  description: string;
  status: ActionStatus;
  progress: number;
  startedAt: string | null;
  updatedAt: string | null;
  source: string;
  projectId: string | null;
  projectName: string | null;
  conversationId: string | null;
  memoryId: string | null;
  taskId: string | null;
  executionId: string | null;
  output: string | null;
  href: string;
  timeline: Array<{ label: string; detail: string; at: string | null }>;
  actionsPerformed: string[];
};

const FILTER_KEY = "synzept-actions-filter";
const REFRESH_MS = 15_000;

export function ActionsPage() {
  const router = useRouter();
  const { dashboard, setDashboard } = useWorkspaceStore();
  const [memory, setMemory] = useState<MemoryExplorerItem[]>([]);
  const [execution, setExecution] = useState<ExecutionState | null>(null);
  const [actionExecutions, setActionExecutions] = useState<ActionExecution[]>([]);
  const [loading, setLoading] = useState(!dashboard);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [selected, setSelected] = useState<SynzeptAction | null>(null);
  const searchParams = useSearchParams();
  const [filter, setFilter] = useState<ActionFilter>("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    const routeFilter = searchParams.get("filter");
    if (routeFilter === "waiting") {
      setFilter("waiting");
    }
  }, [searchParams]);

  const effectiveFilter = filter;

  useEffect(() => {
    const saved = localStorage.getItem(FILTER_KEY);
    if (saved && ["all", "running", "waiting", "completed", "failed"].includes(saved)) setFilter(saved as ActionFilter);
  }, []);

  const load = useCallback(async (background = false) => {
    const workspace = useWorkspaceStore.getState();
    if (background) setRefreshing(true);
    else setLoading(!workspace.dashboard);
    setError(null);
    try {
      const [nextDashboard, nextMemory, nextExecution, nextActions] = await Promise.all([
        workspace.dashboard && workspace.hasFreshDashboard() && !background ? Promise.resolve(workspace.dashboard) : api.getDashboard(),
        api.listMemoryExplorer(false, true).catch(() => []),
        api.getExecutionState().catch(() => null),
        api.listActionExecutions().catch(() => []),
      ]);
      setDashboard(nextDashboard);
      setMemory(nextMemory);
      setExecution(nextExecution);
      setActionExecutions(nextActions);
    } catch {
      setError("Actions could not be refreshed. Existing workspace data is unchanged.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [setDashboard]);

  useEffect(() => { void load(); }, [load]);

  const actions = useMemo(() => buildActions(dashboard, memory, execution, actionExecutions), [actionExecutions, dashboard, execution, memory]);
  const hasRunning = actions.some((action) => action.status === "running");
  const isEmpty = !loading && actions.length === 0;

  useEffect(() => {
    if (!hasRunning) return;
    const timer = window.setInterval(() => void load(true), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [hasRunning, load]);

  const visible = useMemo(() => {
    const clean = query.trim().toLowerCase();
    return actions.filter((action) => (effectiveFilter === "all" || action.status === effectiveFilter) && (!clean || action.title.toLowerCase().includes(clean)));
  }, [actions, effectiveFilter, query]);

  const groups = useMemo(() => ([
    { status: "running" as const, title: "Running", description: "Synzept is actively moving this work forward", icon: LoaderCircle, empty: "Nothing is running right now. Start a new piece of Work when you’re ready." },
    { status: "waiting" as const, title: "Waiting for approval", description: "Your confirmation is required", icon: Clock3, empty: "No approvals yet. Synzept will pause here when it needs your say-so." },
    { status: "completed" as const, title: "Completed", description: "Finished work, ready when you need it", icon: CheckCircle2, empty: "Ask Synzept to do something, and finished Work will appear here." },
    { status: "failed" as const, title: "Needs attention", description: "Work that needs another look", icon: AlertCircle, empty: "Nothing needs your attention right now." },
  ]), []);

  const mutate = async (action: SynzeptAction, operation: "approve" | "reject" | "retry" | "dismiss" | "duplicate") => {
    setBusyId(action.id);
    setError(null);
    try {
      if (operation === "approve" && action.memoryId) await api.approveMemoryCandidate(action.memoryId);
      else if (operation === "reject" && action.memoryId) await api.rejectMemoryCandidate(action.memoryId, "Rejected from Actions.");
      else if (operation === "approve" && action.executionId) await api.approveActionExecution(action.executionId);
      else if (operation === "reject" && action.executionId) await api.rejectActionExecution(action.executionId);
      else if (operation === "approve" && action.taskId) await api.updateTask(action.taskId, { status: "completed" });
      else if (operation === "reject" && action.taskId) await api.updateTask(action.taskId, { status: "archived" });
      else if (operation === "retry" && action.executionId) await api.retryActionExecution(action.executionId);
      else if (operation === "retry" && action.taskId) await api.updateTask(action.taskId, { status: "in_progress" });
      else if (operation === "dismiss" && action.executionId) await api.cancelActionExecution(action.executionId);
      else if (operation === "dismiss" && action.taskId) await api.updateTask(action.taskId, { status: "archived" });
      else if (operation === "duplicate" && action.conversationId) {
        const copy = await api.duplicateConversation(action.conversationId);
        router.push(`/chat?conversation=${copy.id}`);
      } else if (operation === "duplicate" && action.memoryId) {
        const item = memory.find((entry) => entry.memory.id === action.memoryId)?.memory;
        if (item) await api.createMemory({ content: item.content, category: item.category || undefined, memory_type: item.memory_type, project_id: item.project_id, importance: item.importance, pinned: false, archived: false });
      } else if (operation === "duplicate") {
        await api.createTask({ title: `${action.title} (copy)`, description: action.description, project_id: action.projectId || undefined });
      }
      void api.trackEvent(
        operation === "retry" ? "action_retried" : operation === "approve" ? "action_approved" : operation === "reject" ? "action_rejected" : "action_updated",
        "actions",
        { action_status: action.status, action_source: action.source },
      );
      clearSynzeptContextCache();
      setSelected(null);
      await load(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Could not ${operation} this action.`);
    } finally {
      setBusyId(null);
    }
  };

  const reuse = (action: SynzeptAction) => {
    localStorage.setItem("synzept_chat_draft", `Reuse this completed work and adapt it for a new outcome: ${action.title}. ${action.description}`);
    router.push("/chat");
  };

  return (
    <div className="min-h-full bg-[#fbfbfa]">
      <WorkspacePage className="max-w-[1050px] pb-24 pt-10 sm:pt-14">
        <header>
          <div className="flex items-start justify-between gap-4">
            <div><p className="text-xs font-semibold uppercase tracking-[.16em] text-[#58705f]">Work status</p><h1 className="mt-3 text-4xl font-semibold tracking-[-.045em] sm:text-5xl">{effectiveFilter === "waiting" ? "Approvals" : "Work"}</h1><p className="mt-3 max-w-xl text-base leading-7 text-stone-500">See what Synzept is doing, what needs your attention, and what has already been completed.</p></div>
            <button type="button" onClick={() => void load(true)} disabled={refreshing} className="mt-1 grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-stone-200 bg-white text-stone-500 transition hover:text-stone-900 disabled:opacity-50" aria-label="Refresh work"><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /></button>
          </div>
        </header>

        <RecoveryBanner message={error} onRetry={() => void load()} />

        {isEmpty ? (
          <section className="mt-8 rounded-2xl border border-[#dce5de] bg-[#f4f8f5] p-5 sm:p-6" aria-labelledby="actions-empty-title">
            <div className="flex items-start gap-4">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white text-[#4f6b58] shadow-sm"><Sparkles className="h-5 w-5" aria-hidden="true" /></div>
              <div>
                <h2 id="actions-empty-title" className="text-lg font-semibold tracking-[-0.02em] text-stone-900">Your work will appear here.</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-600">Whenever Synzept researches, writes, plans, or summarizes, you can follow the progress here and review anything that needs your approval.</p>
                <Link href="/chat" className="mt-4 inline-flex h-10 items-center rounded-xl bg-stone-900 px-4 text-sm font-medium text-white transition hover:bg-stone-800">Ask Synzept to help</Link>
              </div>
            </div>
          </section>
        ) : null}

        <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex gap-1 overflow-x-auto rounded-xl bg-stone-100 p-1">
            {(["all", "running", "waiting", "completed", "failed"] as const).map((item) => <button key={item} type="button" onClick={() => { setFilter(item); localStorage.setItem(FILTER_KEY, item); }} className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-medium capitalize transition ${filter === item ? "bg-white text-stone-950 shadow-sm" : "text-stone-500 hover:text-stone-800"}`}>{item === "waiting" ? "Waiting for approval" : item === "failed" ? "Needs attention" : item}</button>)}
          </div>
          <label className="relative block sm:w-64"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search work" className="h-10 w-full rounded-xl border border-stone-200 bg-white pl-9 pr-3 text-sm outline-none transition focus:border-[#78907f] focus:ring-2 focus:ring-[#78907f]/10" /></label>
        </div>

        <div className="mt-10 space-y-10">
          {loading ? [1,2,3,4].map((item) => <Skeleton key={item} className="h-40 rounded-2xl" />) : groups.filter((group) => filter === "all" || group.status === filter).map(({ status, title, description, icon: Icon, empty }) => {
            const items = visible.filter((action) => action.status === status);
            return <section key={status}><div className="mb-4 flex items-center gap-3"><div className="grid h-9 w-9 place-items-center rounded-xl bg-white text-stone-600 shadow-sm"><Icon className={`h-4 w-4 ${status === "running" && items.length ? "animate-spin" : ""}`} /></div><div><h2 className="font-semibold">{title}</h2><p className="text-sm text-stone-500">{description}</p></div><span className="ml-auto rounded-full bg-stone-100 px-2.5 py-1 text-xs font-medium text-stone-500">{items.length}</span></div><div className="divide-y divide-stone-100 rounded-2xl border border-stone-200/80 bg-white px-5 shadow-[0_2px_12px_rgba(28,25,23,.035)]">{items.length ? items.map((action) => <ActionRow key={action.id} action={action} busy={busyId === action.id} onSelect={() => setSelected(action)} onOpenDetails={() => action.executionId ? router.push(`/actions/${action.executionId}`) : setSelected(action)} onApprove={() => void mutate(action, "approve")} onReject={() => void mutate(action, "reject")} onRetry={() => void mutate(action, "retry")} onDismiss={() => void mutate(action, "dismiss")} />) : <p className="py-7 text-sm text-stone-500">{query.trim() ? "No actions match your search." : empty}</p>}</div></section>;
          })}
        </div>
      </WorkspacePage>

      {selected && <ActionDetails action={selected} busy={busyId === selected.id} onClose={() => setSelected(null)} onApprove={() => void mutate(selected, "approve")} onReject={() => void mutate(selected, "reject")} onRetry={() => void mutate(selected, "retry")} onDismiss={() => void mutate(selected, "dismiss")} onReuse={() => reuse(selected)} onDuplicate={() => void mutate(selected, "duplicate")} />}
    </div>
  );
}

function ActionRow({ action, busy, onSelect, onOpenDetails, onApprove, onReject, onRetry, onDismiss }: { action: SynzeptAction; busy: boolean; onSelect: () => void; onOpenDetails: () => void; onApprove: () => void; onReject: () => void; onRetry: () => void; onDismiss: () => void }) {
  return <div className="py-4"><button type="button" onClick={onSelect} className="flex w-full items-start gap-4 text-left"><StatusIcon status={action.status} /><div className="min-w-0 flex-1"><div className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium text-stone-950">{action.title}</p><p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{action.description}</p></div><span className="shrink-0 text-xs text-stone-400">{formatRelative(action.updatedAt || action.startedAt)}</span></div>{action.status === "running" && <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-stone-100"><div className="h-full rounded-full bg-[#78907f] transition-all" style={{ width: `${action.progress}%` }} /></div>}<div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-stone-400"><span>{action.source}</span>{action.projectName && <><span>·</span><span>{action.projectName}</span></>}<span>·</span><span>{action.status === "running" ? `Started ${formatRelative(action.startedAt)}` : humanize(action.status)}</span></div></div></button><div className="mt-3 flex flex-wrap gap-2 pl-9">{action.status === "waiting" && <><SmallButton label="Approve" icon={<Check />} disabled={busy} onClick={onApprove} /><SmallButton label="Reject" icon={<X />} disabled={busy} onClick={onReject} /></>}{action.status === "failed" && <><SmallButton label="Retry" icon={<RotateCcw />} disabled={busy || (!action.taskId && !action.executionId)} onClick={onRetry} /><SmallButton label="Dismiss" icon={<XCircle />} disabled={busy || (!action.taskId && !action.executionId)} onClick={onDismiss} /></>}{action.executionId ? <SmallButton label="Open details" icon={<ArrowUpRight />} disabled={busy} onClick={onOpenDetails} /> : <SmallButton label="Open details" icon={<ArrowUpRight />} disabled={busy} onClick={onSelect} />}</div></div>;
}

function ActionDetails({ action, busy, onClose, onApprove, onReject, onRetry, onDismiss, onReuse, onDuplicate }: { action: SynzeptAction; busy: boolean; onClose: () => void; onApprove: () => void; onReject: () => void; onRetry: () => void; onDismiss: () => void; onReuse: () => void; onDuplicate: () => void }) {
  return <div className="fixed inset-0 z-50 flex justify-end bg-stone-950/20 backdrop-blur-[2px]" role="dialog" aria-modal="true" aria-label={`${action.title} details`}><button type="button" className="flex-1" onClick={onClose} aria-label="Close action details" /><aside className="h-full w-full max-w-[480px] overflow-y-auto border-l border-stone-200 bg-[#fbfbfa] p-6 shadow-[-16px_0_40px_rgba(28,25,23,.1)] sm:p-8"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-[.14em] text-[#58705f]">{action.source}</p><h2 className="mt-3 text-2xl font-semibold tracking-[-.03em]">{action.title}</h2></div><button type="button" onClick={onClose} className="grid h-9 w-9 shrink-0 rounded-xl border border-stone-200 bg-white text-stone-500"><X className="h-4 w-4" /></button></div><p className="mt-5 text-sm leading-6 text-stone-600">{action.description}</p>{action.output && <DetailsSection title="Result"><div className="whitespace-pre-wrap rounded-xl border border-stone-200 bg-white p-4 text-sm leading-6 text-stone-700">{action.output}</div></DetailsSection>}<div className="mt-6 grid grid-cols-2 gap-3"><Detail label="Status" value={humanize(action.status)} /><Detail label="Progress" value={`${action.progress}%`} /><Detail label="Created" value={formatFull(action.startedAt)} /><Detail label="Updated" value={formatFull(action.updatedAt)} /></div>{action.status === "running" && <div className="mt-5 h-2 overflow-hidden rounded-full bg-stone-100"><div className="h-full rounded-full bg-[#78907f]" style={{ width: `${action.progress}%` }} /></div>}<div className="mt-7 flex flex-wrap gap-2">{action.status === "waiting" && <><SmallButton label="Approve" icon={<Check />} disabled={busy} onClick={onApprove} /><SmallButton label="Reject" icon={<X />} disabled={busy} onClick={onReject} /></>}{action.status === "failed" && <><SmallButton label="Retry" icon={<RotateCcw />} disabled={busy || (!action.taskId && !action.executionId)} onClick={onRetry} /><SmallButton label="Dismiss" icon={<XCircle />} disabled={busy || (!action.taskId && !action.executionId)} onClick={onDismiss} /></>}{action.status === "completed" && <><SmallButton label="Reuse" icon={<Sparkles />} disabled={busy} onClick={onReuse} /><SmallButton label="Duplicate" icon={<Copy />} disabled={busy} onClick={onDuplicate} /></>}<Link href={action.href} className="inline-flex h-9 items-center gap-2 rounded-xl bg-stone-950 px-3 text-sm font-medium text-white">Open <ArrowUpRight className="h-4 w-4" /></Link></div><DetailsSection title="Related workspace"><div className="space-y-2 text-sm text-stone-600">{action.projectName && <p><span className="text-stone-400">Project:</span> {action.projectName}</p>}{action.conversationId && <p><span className="text-stone-400">Conversation:</span> <Link className="font-medium text-stone-900" href={`/chat?conversation=${action.conversationId}`}>Open conversation</Link></p>}{action.memoryId && <p><span className="text-stone-400">Memory:</span> <Link className="font-medium text-stone-900" href="/memory">Open memory</Link></p>}{!action.projectName && !action.conversationId && !action.memoryId && <p>No related workspace entity.</p>}</div></DetailsSection><DetailsSection title="Timeline"><div className="space-y-4">{action.timeline.map((event, index) => <div key={`${event.label}-${index}`} className="flex gap-3"><span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-[#78907f]" /><div><p className="text-sm font-medium">{event.label}</p><p className="mt-1 text-xs leading-5 text-stone-500">{event.detail}{event.at ? ` · ${formatFull(event.at)}` : ""}</p></div></div>)}</div></DetailsSection><DetailsSection title="Actions performed"><ul className="space-y-2">{action.actionsPerformed.map((item) => <li key={item} className="flex gap-2 text-sm text-stone-600"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#78907f]" />{item}</li>)}</ul></DetailsSection></aside></div>;
}

function buildActions(dashboard: Dashboard | null, memoryItems: MemoryExplorerItem[], execution: ExecutionState | null, executions: ActionExecution[]): SynzeptAction[] {
  if (!dashboard) return [];
  const projectNames = new Map((dashboard.projects || []).map((project) => [project.id, project.name]));
  const taskMap = new Map((dashboard.tasks || []).map((task) => [task.id, task]));
  const executionStatus = new Map<string, ActionStatus>();
  for (const task of execution?.planned || []) executionStatus.set(task.id, "running");
  for (const task of execution?.completed || []) executionStatus.set(task.id, "completed");
  for (const task of execution?.blocked || []) executionStatus.set(task.id, "failed");
  const actions: SynzeptAction[] = (dashboard.tasks || [])
    .filter((task) => executionStatus.has(task.id) || isOperationalTask(task))
    .map((task) => fromTask(task, projectNames.get(task.project_id || "") || null, executionStatus.get(task.id)));

  for (const item of memoryItems) {
    const status = memoryStatus(item);
    if (status === "candidate") actions.push(fromMemoryCandidate(item, projectNames));
    for (const event of item.timeline.filter((entry) => ["approved", "confirmed", "merged"].includes(entry.action)).slice(0, 2)) actions.push(fromMemoryEvent(item, event, projectNames));
  }

  for (const task of execution?.completed || []) if (!taskMap.has(task.id)) actions.push(fromExecution(task, "completed", projectNames));
  for (const task of execution?.blocked || []) if (!taskMap.has(task.id)) actions.push(fromExecution(task, "failed", projectNames));
  for (const task of execution?.planned || []) if (!taskMap.has(task.id)) actions.push(fromExecution(task, "running", projectNames));
  for (const action of executions) actions.push(fromActionExecution(action, projectNames));

  const seen = new Set<string>();
  return actions.filter((action) => {
    const key = action.memoryId ? `${action.memoryId}:${action.status}:${action.updatedAt}` : action.taskId ? `task:${action.taskId}` : `${action.source}:${action.title}:${action.status}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  }).sort((left, right) => dateValue(right.updatedAt || right.startedAt) - dateValue(left.updatedAt || left.startedAt));
}

function fromTask(task: Task, projectName: string | null, executionOverride?: ActionStatus): SynzeptAction {
  const rawStatus = task.status as string;
  const status: ActionStatus = executionOverride || (rawStatus === "in_progress" ? "running" : rawStatus === "pending" ? "waiting" : ["completed", "done"].includes(rawStatus) ? "completed" : "failed");
  const progress = status === "completed" ? 100 : status === "running" ? 50 : status === "waiting" ? 80 : 0;
  return { id: `task-${task.id}`, title: task.title, description: task.description || taskDescription(status), status, progress, startedAt: task.created_at, updatedAt: task.updated_at || task.created_at, source: executionOverride ? "Autonomous workspace" : "Workspace task", projectId: task.project_id, projectName, conversationId: null, memoryId: null, taskId: task.id, executionId: null, output: null, href: task.project_id ? `/projects/${task.project_id}` : "/tasks", timeline: taskTimeline(task, status), actionsPerformed: status === "completed" ? ["Work completed", "Result saved to the workspace"] : status === "failed" ? ["Execution started", "Execution stopped before completion"] : ["Action created", status === "running" ? "Execution is in progress" : "Paused for user approval"] };
}

function fromMemoryCandidate(item: MemoryExplorerItem, projectNames: Map<string, string>): SynzeptAction {
  const memory = item.memory;
  const projectName = item.connected_projects[0]?.title || (memory.project_id ? projectNames.get(memory.project_id) : null) || null;
  return { id: `memory-candidate-${memory.id}`, title: `Approve memory: ${memory.summary || truncate(memory.content, 72)}`, description: memory.content, status: "waiting", progress: 80, startedAt: memory.created_at, updatedAt: memory.updated_at, source: "Memory intelligence", projectId: memory.project_id, projectName, conversationId: conversationSource(memory), memoryId: memory.id, taskId: null, executionId: null, output: null, href: "/memory", timeline: item.timeline.map(fromMemoryTimeline), actionsPerformed: ["Detected a potentially useful memory", "Checked it against existing understanding", "Paused before saving it as approved memory"] };
}

function fromMemoryEvent(item: MemoryExplorerItem, event: MemoryTrustEvent, projectNames: Map<string, string>): SynzeptAction {
  const memory = item.memory;
  const projectName = item.connected_projects[0]?.title || (memory.project_id ? projectNames.get(memory.project_id) : null) || null;
  return { id: `memory-event-${event.id}`, title: event.action === "merged" ? `Memory organized: ${memory.summary || truncate(memory.content, 64)}` : `Memory ${event.action}: ${memory.summary || truncate(memory.content, 64)}`, description: event.reason || memory.content, status: "completed", progress: 100, startedAt: memory.created_at, updatedAt: event.created_at, source: "Memory intelligence", projectId: memory.project_id, projectName, conversationId: conversationSource(memory), memoryId: memory.id, taskId: null, executionId: null, output: null, href: "/memory", timeline: item.timeline.map(fromMemoryTimeline), actionsPerformed: ["Reviewed the memory signal", humanize(event.action), "Updated Synzept’s approved understanding"] };
}

function fromExecution(task: ExecutionState["planned"][number], status: ActionStatus, projectNames: Map<string, string>): SynzeptAction {
  return { id: `execution-${task.id}-${status}`, title: task.title, description: status === "failed" ? "Execution is blocked and needs attention." : status === "completed" ? "Autonomous execution completed successfully." : "Autonomous work is queued or in progress.", status, progress: status === "completed" ? 100 : status === "failed" ? 0 : 35, startedAt: null, updatedAt: null, source: "Autonomous workspace", projectId: task.project_id, projectName: task.project_id ? projectNames.get(task.project_id) || null : null, conversationId: null, memoryId: null, taskId: task.id, executionId: null, output: null, href: task.project_id ? `/projects/${task.project_id}` : "/autonomous-workspace", timeline: [{ label: "Execution planned", detail: task.title, at: null }, { label: humanize(status), detail: status === "failed" ? "The execution could not continue." : "Latest execution state.", at: null }], actionsPerformed: ["Created an execution step", status === "completed" ? "Completed the step" : status === "failed" ? "Recorded the blocker" : "Started execution"] };
}

function fromActionExecution(action: ActionExecution, projectNames: Map<string, string>): SynzeptAction {
  const status: ActionStatus = action.status === "queued" || action.status === "running" ? "running" : action.status === "waiting_approval" ? "waiting" : action.status === "completed" ? "completed" : "failed";
  return { id: `ai-execution-${action.id}`, title: action.title, description: action.error || action.output || action.request, status, progress: action.progress, startedAt: action.created_at, updatedAt: action.updated_at, source: "Synzept execution", projectId: action.project_id, projectName: action.project_id ? projectNames.get(action.project_id) || null : null, conversationId: action.conversation_id, memoryId: null, taskId: null, executionId: action.id, output: action.output, href: "/actions", timeline: [{ label: "Action created", detail: action.request, at: action.created_at }, { label: humanize(action.status), detail: action.error || (action.output ? "Result saved and ready to reopen." : "AI execution is in progress."), at: action.updated_at }], actionsPerformed: action.status === "completed" ? ["Completed AI work", "Saved the result to this action"] : action.status === "failed" ? ["Execution stopped", "Retry is available"] : ["Created from chat", "Running in the background"] };
}

function StatusIcon({ status }: { status: ActionStatus }) { if (status === "running") return <LoaderCircle className="mt-0.5 h-5 w-5 shrink-0 animate-spin text-[#58705f]" />; if (status === "waiting") return <Clock3 className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />; if (status === "failed") return <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />; return <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" />; }
function SmallButton({ label, icon, disabled, onClick }: { label: string; icon: React.ReactNode; disabled?: boolean; onClick: () => void }) { return <button type="button" disabled={disabled} onClick={onClick} className="inline-flex h-9 items-center gap-2 rounded-xl border border-stone-200 bg-white px-3 text-xs font-medium text-stone-600 transition hover:border-stone-300 hover:text-stone-950 disabled:opacity-45">{icon && <span className="[&>svg]:h-3.5 [&>svg]:w-3.5">{icon}</span>}{label}</button>; }
function Detail({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-stone-200 bg-white p-3"><p className="text-[11px] text-stone-400">{label}</p><p className="mt-1 text-sm font-medium text-stone-800">{value}</p></div>; }
function DetailsSection({ title, children }: { title: string; children: React.ReactNode }) { return <section className="mt-8 border-t border-stone-200 pt-6"><h3 className="mb-4 flex items-center gap-2 text-sm font-semibold"><History className="h-4 w-4 text-stone-400" />{title}</h3>{children}</section>; }
function memoryStatus(item: MemoryExplorerItem) { const value = item.memory.metadata?.understanding_status; return typeof value === "string" ? value : item.memory.archived_at ? "archived" : "active"; }
function conversationSource(memory: MemoryExplorerItem["memory"]) { const value = memory.metadata?.conversation_id || memory.metadata?.source_conversation_id; return typeof value === "string" ? value : null; }
function fromMemoryTimeline(event: MemoryTrustEvent) { return { label: humanize(event.action), detail: event.reason || "Memory state updated.", at: event.created_at }; }
function taskTimeline(task: Task, status: ActionStatus) { return [{ label: "Action created", detail: task.description || task.title, at: task.created_at }, { label: humanize(status), detail: taskDescription(status), at: task.created_at }]; }
function taskDescription(status: ActionStatus) { return status === "running" ? "Work is currently in progress." : status === "waiting" ? "Waiting for user confirmation." : status === "failed" ? "Work stopped and needs attention." : "Work completed successfully."; }
function isOperationalTask(task: Task) { const status = task.status as string; if (["in_progress", "pending", "failed", "blocked", "error"].includes(status)) return true; return ["completed", "done"].includes(status) && /\b(ai|synzept|research|summary|summarize|draft|generate|organize|prepare|proposal|presentation|meeting brief|document)\b/i.test(`${task.title} ${task.description || ""}`); }
function truncate(value: string, length: number) { return value.length > length ? `${value.slice(0, length - 1).trim()}…` : value; }
function humanize(value: string) { return value.replace(/[_-]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function dateValue(value: string | null) { if (!value) return 0; const parsed = new Date(value).getTime(); return Number.isFinite(parsed) ? parsed : 0; }
function formatRelative(value: string | null) { if (!value) return "Recently"; const date = new Date(value); if (Number.isNaN(date.getTime())) return "Recently"; const diff = Date.now() - date.getTime(); if (diff < 60_000) return "now"; if (diff < 3_600_000) return `${Math.max(1, Math.floor(diff / 60_000))}m ago`; if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`; if (diff < 604_800_000) return `${Math.floor(diff / 86_400_000)}d ago`; return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date); }
function formatFull(value: string | null) { if (!value) return "Not recorded"; const date = new Date(value); return Number.isNaN(date.getTime()) ? "Not recorded" : new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(date); }

"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, Check, Clock3, Loader2, Pencil, Search, Send, Sparkles } from "lucide-react";
import { WorkspacePage } from "@/components/layout/workspace-content";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ActionExecution, type Project, type Task } from "@/lib/api";
import { buildWorkExecutionNarrative, buildWorkItems, type WorkItem, type WorkStatus } from "@/lib/work";
import { cn } from "@/lib/cn";

const filters: Array<{ key: string; label: string }> = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "waiting_for_approval", label: "Waiting" },
  { key: "completed", label: "Completed" },
  { key: "failed", label: "Needs attention" },
];

const examplePrompts = [
  "Research competitors and summarize the top three",
  "Draft a first pass of a customer update",
  "Review this project and surface the next best step",
];

export function WorkPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [executions, setExecutions] = useState<ActionExecution[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [draft, setDraft] = useState("");
  const [creating, setCreating] = useState(false);

  const load = async (background = false) => {
    if (!background) setLoading(true);
    setError(null);
    try {
      const [taskRows, projectRows, executionRows] = await Promise.all([
        api.listTasks(),
        api.listProjects().catch(() => []),
        api.listActionExecutions().catch(() => []),
      ]);
      setTasks(taskRows);
      setProjects(projectRows);
      setExecutions(executionRows);
    } catch {
      setError("Work could not load. Please retry when the connection settles.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    const activeWork = executions.some((execution) => ["queued", "running", "waiting_approval"].includes(execution.status));
    if (!activeWork) return;
    const interval = window.setInterval(() => {
      void api.listActionExecutions().then((rows) => {
        setExecutions((current) => (current.length === rows.length && current.every((item, index) => item.id === rows[index]?.id && item.status === rows[index]?.status)) ? current : rows);
      }).catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(interval);
  }, [executions]);

  const workItems = useMemo(() => buildWorkItems(tasks, executions, projects), [tasks, executions, projects]);

  const visibleItems = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return workItems.filter((item) => {
      const matchesSearch = !normalized || item.title.toLowerCase().includes(normalized) || item.summary.toLowerCase().includes(normalized);
      const matchesFilter =
        filter === "all" ||
        (filter === "active" && ["created", "planning", "working", "waiting_for_approval"].includes(item.status)) ||
        item.status === filter;
      return matchesSearch && matchesFilter;
    });
  }, [workItems, query, filter]);

  const groups = useMemo<Array<{ title: string; statuses: WorkStatus[]; hint: string }>>(
    () => [
      { title: "Active Work", statuses: ["created", "planning", "working"], hint: "Work that Synzept is currently moving forward." },
      { title: "Waiting for Approval", statuses: ["waiting_for_approval"], hint: "Work that needs your confirmation before Synzept continues." },
      { title: "Completed Work", statuses: ["completed"], hint: "Work that Synzept has finished for you." },
      { title: "Needs attention", statuses: ["failed"], hint: "Work that needs another review or retry." },
    ],
    [],
  );

  const createWork = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!draft.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await api.createActionExecution({ request: draft.trim() });
      setDraft("");
      await load(true);
    } catch {
      setError("Work could not be created. Your input is still here; try again.");
    } finally {
      setCreating(false);
    }
  };

  const activeCount = workItems.filter((item) => ["created", "planning", "working", "waiting_for_approval"].includes(item.status)).length;
  const completedCount = workItems.filter((item) => item.status === "completed").length;
  const approvalCount = workItems.filter((item) => item.status === "waiting_for_approval").length;

  return (
    <div className="min-h-full bg-[#faf9f6] text-stone-950">
      <WorkspacePage className="!max-w-[1050px] !pb-24 !pt-10 sm:!pt-14">
        <header className="pb-6">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#54705c]">Work</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.045em] text-stone-950">Execution feed</h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-600">Delegate a goal and Synzept will turn it into a plan, keep progress visible, and ask for approval only when it matters.</p>
        </header>

        <RecoveryBanner message={error} onRetry={() => void load()} />

        <section className="rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
          <form onSubmit={createWork} className="grid gap-3">
            <label className="block text-sm font-semibold text-stone-900" htmlFor="work-input">What do you want Synzept to do?</label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input
                id="work-input"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Book my train tomorrow."
                className="min-w-0 flex-1 rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3 text-sm text-stone-900 outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-[#8ca58f]/30"
              />
              <button type="submit" disabled={creating} className="inline-flex h-12 items-center justify-center rounded-3xl bg-stone-950 px-6 text-sm font-semibold text-white transition hover:bg-stone-800 disabled:opacity-50">
                {creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                Start execution
              </button>
            </div>
            <p className="text-sm text-stone-500">Synzept will infer the plan, execution path, and approval needs automatically.</p>
            <div className="flex flex-wrap gap-2">
              {examplePrompts.map((prompt) => (
                <span key={prompt} className="rounded-full border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-600">
                  {prompt}
                </span>
              ))}
            </div>
          </form>
        </section>

        <section className="mt-6 grid gap-4 sm:grid-cols-3">
          <SummaryCard label="Active" value={activeCount} description="Work currently in motion." />
          <SummaryCard label="Waiting" value={approvalCount} description="Work paused for your approval." />
          <SummaryCard label="Completed" value={completedCount} description="Work finished today or earlier." />
        </section>

        <section className="mt-6 rounded-[32px] border border-stone-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-stone-900">Execution feed</p>
              <p className="mt-1 text-sm text-stone-500">Search, filter, and open the work Synzept is owning for you.</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="relative block">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-stone-400" />
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Search work"
                  className="h-11 rounded-3xl border border-stone-200 bg-stone-50 px-10 text-sm text-stone-900 outline-none transition focus:border-stone-400 focus:ring-2 focus:ring-[#8ca58f]/30"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                {filters.map((option) => (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => setFilter(option.key)}
                    className={cn(
                      "rounded-full px-4 py-2 text-sm transition",
                      filter === option.key ? "bg-stone-950 text-white" : "bg-stone-100 text-stone-700 hover:bg-stone-200",
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="mt-8 space-y-10">
            {loading ? (
              Array.from({ length: 3 }, (_, index) => <Skeleton key={index} className="h-40 rounded-3xl" />)
            ) : workItems.length === 0 ? (
              <div className="rounded-[32px] border border-dashed border-stone-200 bg-stone-50 px-6 py-12 text-center">
                <p className="text-lg font-semibold text-stone-950">No executions yet.</p>
                <p className="mt-3 text-sm leading-7 text-stone-600">Delegate your first goal by telling Synzept what you want accomplished. It will turn the request into a plan, keep progress visible, and surface outcomes when they are ready.</p>
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {examplePrompts.map((prompt) => (
                    <button key={prompt} type="button" onClick={() => setDraft(prompt)} className="rounded-full border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700 transition hover:border-stone-300 hover:text-stone-900">
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : visibleItems.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-stone-200 bg-stone-50 px-6 py-12 text-center text-sm text-stone-500">No work matches this view. Try a different filter or clear the search.</div>
            ) : (
              groups.map((group) => {
                const items = visibleItems.filter((item) => group.statuses.includes(item.status));
                if (!items.length) return null;
                return (
                  <div key={group.title} className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                      <div>
                        <p className="text-sm font-semibold text-stone-900">{group.title}</p>
                        <p className="mt-1 text-sm text-stone-500">{group.hint}</p>
                      </div>
                      <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">{items.length}</span>
                    </div>
                    <div className="mt-5 space-y-4">
                      {items.map((item) => (
                        <WorkCard key={item.id} item={item} execution={item.actionId ? executions.find((execution) => execution.id === item.actionId) : undefined} onUpdated={() => void load(true)} />
                      ))}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </WorkspacePage>
    </div>
  );
}

function SummaryCard({ label, value, description }: { label: string; value: number; description: string }) {
  return (
    <div className="rounded-[28px] border border-stone-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">{label}</p>
      <p className="mt-4 text-3xl font-semibold text-stone-950">{value}</p>
      <p className="mt-2 text-sm text-stone-500">{description}</p>
    </div>
  );
}

type EmailDraft = { from?: string; to?: string; subject?: string; context?: string; reason?: string; suggested_reply?: string };

function WorkCard({ item, execution, onUpdated }: { item: WorkItem; execution?: ActionExecution; onUpdated: () => void }) {
  const [editing, setEditing] = useState<number | null>(null);
  const [saving, setSaving] = useState<number | null>(null);
  const [replyEdits, setReplyEdits] = useState<Record<number, string>>({});
  const story = buildWorkExecutionNarrative(item);
  const lastUpdated = new Date(item.updated_at || item.created_at).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
  const dueDate = item.due_at ? new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(item.due_at)) : null;
  const preview = item.output ? item.output.replace(/\s+/g, " ").slice(0, 140) : item.detail ? item.detail.replace(/\s+/g, " ").slice(0, 140) : item.summary.replace(/\s+/g, " ").slice(0, 140);
  const emailWork = execution?.action_type === "email_work" ? execution.metadata.email_work as { drafts?: EmailDraft[]; approved_draft_indices?: number[]; sent?: Array<{ message_id?: string }> } | undefined : undefined;
  const emailDrafts = emailWork?.drafts || [];
  const canReview = execution?.status === "awaiting_confirmation";

  const saveDraft = async (index: number, draft: EmailDraft) => {
    setSaving(index);
    try {
      const updated = await api.updateEmailDraft(execution!.id, index, { suggested_reply: replyEdits[index] ?? draft.suggested_reply });
      setEditing(null);
      onUpdated();
      void updated;
    } catch {
      // The parent recovery banner remains the single error surface for Work.
    } finally {
      setSaving(null);
    }
  };

  const approveDraft = async (index: number) => {
    setSaving(index);
    try {
      await api.approveActionExecution(execution!.id, [index]);
      onUpdated();
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="rounded-[28px] border border-stone-200 bg-white p-5 transition hover:border-stone-300 hover:shadow-sm">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-600">{item.statusLabel}</span>
            {item.approvalRequired ? <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-amber-700">Needs approval</span> : null}
          </div>
          <p className="mt-3 text-base font-semibold text-stone-950">{story.headline}</p>
          <p className="mt-2 text-sm leading-6 text-stone-600">{story.activity}</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-stone-100 bg-stone-50 px-3 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">Why it matters</p>
              <p className="mt-1 text-sm text-stone-700">{story.why}</p>
            </div>
            <div className="rounded-2xl border border-stone-100 bg-stone-50 px-3 py-3">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">What happens next</p>
              <p className="mt-1 text-sm text-stone-700">{story.nextStep}</p>
            </div>
          </div>
          <div className="mt-4 rounded-2xl border border-stone-100 bg-[#f7f7f2] px-3 py-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">Current status</p>
            <p className="mt-1 text-sm text-stone-700">{preview}{preview.length >= 140 ? "…" : ""}</p>
          </div>
        </div>

        <div className="w-full max-w-[240px] space-y-3">
          <div className="rounded-2xl border border-stone-100 bg-[#fcfdfc] p-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-stone-500">Progress</span>
              <span className="font-semibold text-stone-900">{item.progress}%</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-stone-100">
              <div className="h-full rounded-full bg-[#78907f] transition-all" style={{ width: `${item.progress}%` }} />
            </div>
          </div>

          <div className="space-y-2 text-sm text-stone-600">
            <div className="flex items-center gap-2">
              <Clock3 className="h-4 w-4 text-stone-400" />
              <span>Updated {lastUpdated}</span>
            </div>
            <div className="flex items-center gap-2">
              <CalendarDays className="h-4 w-4 text-stone-400" />
              <span>{dueDate ? `Due ${dueDate}` : item.approvalRequired ? "Approval pending" : "No deadline"}</span>
            </div>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-stone-400" />
              <span>{item.projectName ?? "No project"}</span>
            </div>
          </div>
        </div>
      </div>

      {emailDrafts.length ? (
        <div className="mt-5 border-t border-stone-100 pt-5">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm font-semibold text-stone-900">Reply drafts</p>
            <p className="text-xs text-stone-500">Drafting never sends. Each reply needs your approval.</p>
          </div>
          <div className="mt-4 space-y-3">
            {emailDrafts.map((emailDraft, index) => (
              <div key={`${emailDraft.to}-${index}`} className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                <div className="grid gap-3 text-sm sm:grid-cols-2">
                  <EmailField label="From" value={emailDraft.from || emailDraft.to || "Unknown sender"} />
                  <EmailField label="Subject" value={emailDraft.subject || "(no subject)"} />
                </div>
                <EmailField label="Context" value={emailDraft.context || "No preview available."} />
                <EmailField label="Why it needs attention" value={emailDraft.reason || "Needs your response"} />
                <div className="mt-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">Suggested reply</p>
                  {editing === index ? (
                    <textarea value={replyEdits[index] ?? emailDraft.suggested_reply ?? ""} onChange={(event) => setReplyEdits((current) => ({ ...current, [index]: event.target.value }))} className="mt-2 min-h-24 w-full rounded-xl border border-stone-200 bg-white px-3 py-2 text-sm text-stone-800 outline-none focus:border-stone-400" />
                  ) : <p className="mt-1 text-sm leading-6 text-stone-700">{emailDraft.suggested_reply || "No reply was generated."}</p>}
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {editing === index ? (
                    <button type="button" disabled={saving === index} onClick={() => void saveDraft(index, emailDraft)} className="inline-flex items-center rounded-full bg-stone-950 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"><Check className="mr-1.5 h-3.5 w-3.5" />Save reply</button>
                  ) : <button type="button" disabled={!canReview} onClick={() => setEditing(index)} className="inline-flex items-center rounded-full border border-stone-200 px-3 py-2 text-xs font-semibold text-stone-700 disabled:opacity-50"><Pencil className="mr-1.5 h-3.5 w-3.5" />Review/Edit</button>}
                  {canReview ? <button type="button" disabled={saving === index} onClick={() => void approveDraft(index)} className="inline-flex items-center rounded-full bg-[#54705c] px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"><Send className="mr-1.5 h-3.5 w-3.5" />Approve</button> : null}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-5 flex flex-col gap-3 border-t border-stone-100 pt-4 text-sm text-stone-600 sm:flex-row sm:items-center sm:justify-between">
        <p>{item.approvalRequired ? "Waiting for your decision before the next step proceeds." : item.status === "completed" ? "Ready for review and reuse." : story.estimate}</p>
        <Link href={`/actions/${item.id}`} className="inline-flex items-center gap-1 font-medium text-stone-900">Open work <ArrowRight className="h-4 w-4" /></Link>
      </div>
    </div>
  );
}

function EmailField({ label, value }: { label: string; value: string }) {
  return <div className="mt-3"><p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">{label}</p><p className="mt-1 text-sm leading-6 text-stone-700">{value}</p></div>;
}

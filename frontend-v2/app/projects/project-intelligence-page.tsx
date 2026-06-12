"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquare, Plus, Save } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useChatStore } from "@/stores/chat";
import { IntelligenceSection } from "../../components/project-intelligence/intelligence-section";
import { projectIntelligenceApi } from "../../lib/project-intelligence";
import type { ProjectDecision, ProjectIntelligencePage, ProjectOpenLoop } from "../../types/project-intelligence";

export function ProjectIntelligencePage({ projectId }: { projectId: string }) {
  const [page, setPage] = useState<ProjectIntelligencePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState("");
  const [focus, setFocus] = useState("");
  const [nextStep, setNextStep] = useState("");
  const [decision, setDecision] = useState("");
  const [loop, setLoop] = useState("");
  const setActiveProject = useChatStore((state) => state.setActiveProject);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await projectIntelligenceApi.get(projectId);
      setPage(data);
      setSummary(data.project_summary);
      setFocus(data.current_focus);
      setNextStep(data.recommended_next_step);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Synzept could not load this project.");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  const save = async () => {
    if (!page) return;
    setSaving(true);
    setError(null);
    try {
      await projectIntelligenceApi.update(projectId, {
        summary: summary.trim(),
        current_focus: focus.trim(),
        recommended_next_step: nextStep.trim(),
        status: page.status,
      });
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Synzept could not save this project.");
    } finally {
      setSaving(false);
    }
  };

  const createDecision = async (event: FormEvent) => {
    event.preventDefault();
    if (!decision.trim()) return;
    await projectIntelligenceApi.createDecision(projectId, decision.trim());
    setDecision("");
    await load();
  };

  const createLoop = async (event: FormEvent) => {
    event.preventDefault();
    if (!loop.trim()) return;
    await projectIntelligenceApi.createLoop(projectId, loop.trim());
    setLoop("");
    await load();
  };

  if (loading && !page) {
    return <div className="space-y-4 p-6"><Skeleton className="h-28 w-full" /><Skeleton className="h-52 w-full" /></div>;
  }

  if (!page) {
    return <p className="p-6 text-sm text-red-700">{error || "Project not found."}</p>;
  }

  const openDecisions = page.decisions.filter((item) => item.status === "open");
  const openLoops = page.open_loops.filter((item) => item.status === "open");

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-5xl px-4 py-7 sm:px-6 md:py-9">
        <header className="border-b border-border pb-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Project Intelligence</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">{page.project_name}</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-stone-600">{page.project_summary}</p>
              <p className="mt-2 text-xs text-muted">Last activity: {formatDate(page.last_activity)}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <select
                value={page.status}
                onChange={(event) => setPage({ ...page, status: event.target.value as ProjectIntelligencePage["status"] })}
                className="h-8 rounded-lg border border-border bg-white px-3 text-xs font-medium capitalize text-stone-700 outline-none"
              >
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="completed">Completed</option>
              </select>
              <Link href="/chat" onClick={() => setActiveProject(projectId)}>
                <Button size="sm" variant="outline"><MessageSquare className="mr-1.5 h-4 w-4" />Continue</Button>
              </Link>
              <Button size="sm" onClick={save} disabled={saving}><Save className="mr-1.5 h-4 w-4" />Save</Button>
            </div>
          </div>
        </header>

        {error && <p className="mt-5 rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        {page.risk.level !== "low" && <p className="mt-5 rounded-lg border border-amber-100 bg-amber-50 px-4 py-3 text-sm text-amber-900"><span className="font-medium capitalize">{page.risk.level} risk:</span> {page.risk.reasons.join(" ")}</p>}

        <main className="mt-5 space-y-4">
          <IntelligenceSection title="Current Focus" description="What is the most important thing happening in this project right now?">
            <Textarea value={focus} onChange={(event) => setFocus(event.target.value)} className="min-h-20 resize-y" />
          </IntelligenceSection>

          <IntelligenceSection title="Recent Activity" description="Conversations, notes, memory, and tasks. Newest first.">
            <ActivityList items={page.recent_activity} />
          </IntelligenceSection>

          <IntelligenceSection title="Open Decisions" description="Important choices that have not been finalized.">
            <form onSubmit={createDecision} className="mb-4 flex gap-2">
              <Input value={decision} onChange={(event) => setDecision(event.target.value)} placeholder="Add a decision to resolve" />
              <Button size="sm" type="submit"><Plus className="mr-1 h-4 w-4" />Create</Button>
            </form>
            <DecisionList items={openDecisions} onChange={async (id, data) => { await projectIntelligenceApi.updateDecision(projectId, id, data); await load(); }} />
          </IntelligenceSection>

          <IntelligenceSection title="Open Loops" description="Things started but unfinished.">
            <form onSubmit={createLoop} className="mb-4 flex gap-2">
              <Input value={loop} onChange={(event) => setLoop(event.target.value)} placeholder="Add an unfinished thread" />
              <Button size="sm" type="submit"><Plus className="mr-1 h-4 w-4" />Create</Button>
            </form>
            <LoopList items={openLoops} onChange={async (id, data) => { await projectIntelligenceApi.updateLoop(projectId, id, data); await load(); }} />
          </IntelligenceSection>

          <IntelligenceSection title="Recommended Next Step" description="Keep this concise: one clear action.">
            <Textarea value={nextStep} onChange={(event) => setNextStep(event.target.value)} className="min-h-16 resize-y" />
          </IntelligenceSection>

          <div className="grid gap-4 lg:grid-cols-2">
            <IntelligenceSection title="Related Conversations" description="Linked AI threads.">
              <ul className="space-y-3">
                {page.conversations.map((item) => (
                  <li key={item.id} className="rounded-lg bg-stone-50 px-3 py-3">
                    <p className="text-sm font-medium text-stone-800">{item.title}</p>
                    {item.summary && <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{item.summary}</p>}
                    <Link href={`/chat?conversation=${item.id}`} onClick={() => setActiveProject(projectId)} className="mt-2 inline-block text-xs font-medium text-accent-foreground hover:underline">Open Thread</Link>
                  </li>
                ))}
                {!page.conversations.length && <li className="text-sm text-stone-400">No linked conversations yet.</li>}
              </ul>
            </IntelligenceSection>

            <IntelligenceSection title="Related Memory" description="Goals, decisions, and context connected to this project.">
              <ul className="space-y-3">
                {page.memories.map((item) => (
                  <li key={item.id} className="rounded-lg bg-stone-50 px-3 py-3">
                    <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{item.title}</p>
                    <p className="mt-1 text-sm leading-6 text-stone-700">{item.content}</p>
                  </li>
                ))}
                {!page.memories.length && <li className="text-sm text-stone-400">No related memory yet.</li>}
              </ul>
            </IntelligenceSection>
          </div>

          <IntelligenceSection title="Project Summary" description="A concise explanation of what this project is.">
            <Textarea value={summary} onChange={(event) => setSummary(event.target.value)} className="min-h-24 resize-y" />
          </IntelligenceSection>
        </main>
      </div>
    </div>
  );
}

function ActivityList({ items }: { items: ProjectIntelligencePage["recent_activity"] }) {
  return <ul className="divide-y divide-border">{items.map((item) => <li key={`${item.type}-${item.id}`} className="py-3 first:pt-0"><div className="flex items-center gap-2"><Badge variant="muted">{item.type}</Badge><p className="text-sm font-medium text-stone-800">{item.title}</p></div>{item.detail && <p className="mt-1 text-xs leading-5 text-muted">{item.detail}</p>}</li>)}{!items.length && <li className="text-sm text-stone-400">No recent project activity yet.</li>}</ul>;
}

function DecisionList({ items, onChange }: { items: ProjectDecision[]; onChange: (id: string, data: Partial<Pick<ProjectDecision, "decision" | "status">>) => Promise<void> }) {
  return <ul className="space-y-2">{items.map((item) => <li key={item.id} className="flex flex-col gap-2 rounded-lg bg-stone-50 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"><Input defaultValue={item.decision} onBlur={(event) => event.target.value.trim() !== item.decision && void onChange(item.id, { decision: event.target.value.trim() })} className="border-0 bg-transparent px-0 focus:ring-0" /><Button size="sm" variant="ghost" onClick={() => void onChange(item.id, { status: "resolved" })}>Resolve</Button></li>)}{!items.length && <li className="text-sm text-stone-400">No open decisions.</li>}</ul>;
}

function LoopList({ items, onChange }: { items: ProjectOpenLoop[]; onChange: (id: string, data: Partial<Pick<ProjectOpenLoop, "loop" | "status">>) => Promise<void> }) {
  return <ul className="space-y-2">{items.map((item) => <li key={item.id} className="flex flex-col gap-2 rounded-lg bg-stone-50 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"><Input defaultValue={item.loop} onBlur={(event) => event.target.value.trim() !== item.loop && void onChange(item.id, { loop: event.target.value.trim() })} className="border-0 bg-transparent px-0 focus:ring-0" /><Button size="sm" variant="ghost" onClick={() => void onChange(item.id, { status: "closed" })}>Close</Button></li>)}{!items.length && <li className="text-sm text-stone-400">No open loops.</li>}</ul>;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

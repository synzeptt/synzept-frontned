"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { CircleHelp, EyeOff, Link2, Merge, PencilLine, Search, ShieldAlert, Trash2 } from "lucide-react";
import { PageFrame } from "@frontend/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, type MemoryExplain, type MemoryExplorerItem } from "@/lib/api";
import { cn } from "@/lib/cn";

export function MemoryPage() {
  const [items, setItems] = useState<MemoryExplorerItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [includeIgnored, setIncludeIgnored] = useState(false);
  const [search, setSearch] = useState("");
  const [editContent, setEditContent] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editImportance, setEditImportance] = useState("0.5");
  const [editReason, setEditReason] = useState("");
  const [mergeSourceId, setMergeSourceId] = useState("");
  const [mergeReason, setMergeReason] = useState("");
  const [messageId, setMessageId] = useState("");
  const [explanation, setExplanation] = useState<MemoryExplain | null>(null);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const [explanationLoading, setExplanationLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listMemoryExplorer(includeIgnored);
      setItems(rows);
      setSelectedId((current) => rows.some((item) => item.memory.id === current) ? current : rows[0]?.memory.id ?? null);
    } catch {
      setError("Memory explorer could not load. Your memories are still safe; retry when the connection settles.");
    } finally {
      setLoading(false);
    }
  }, [includeIgnored]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = useMemo(() => items.find((item) => item.memory.id === selectedId) || null, [items, selectedId]);

  useEffect(() => {
    if (!selected) return;
    setEditContent(selected.memory.content);
    setEditCategory(selected.memory.category || selected.memory.memory_type);
    setEditImportance(String(selected.memory.importance));
    setEditReason("");
    setMergeSourceId("");
    setMergeReason("");
  }, [selected]);

  const visibleItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    const sorted = items.slice().sort((a, b) => b.memory.updated_at.localeCompare(a.memory.updated_at));
    if (!query) return sorted;
    return sorted.filter((item) => {
      const projectText = item.connected_projects.map((project) => project.title).join(" ");
      const goalText = item.connected_goals.map((goal) => goal.title).join(" ");
      return [item.memory.content, item.memory.summary, item.memory.source, item.memory.category, projectText, goalText]
        .some((value) => value?.toLowerCase().includes(query));
    });
  }, [items, search]);

  const saveMemory = async (event: FormEvent) => {
    event.preventDefault();
    if (!selected) return;
    setError(null);
    try {
      await api.updateMemoryV2(selected.memory.id, {
        content: editContent.trim(),
        category: editCategory.trim() || null,
        importance: Number.parseFloat(editImportance),
        reason: editReason.trim() || null,
      });
      await load();
    } catch {
      setError("Memory update could not be saved. Your edits are still here.");
    }
  };

  const mergeMemory = async () => {
    if (!selected || !mergeSourceId || mergeSourceId === selected.memory.id) return;
    setError(null);
    try {
      await api.mergeMemory(selected.memory.id, {
        source_memory_id: mergeSourceId,
        reason: mergeReason.trim() || null,
      });
      await load();
    } catch {
      setError("Memory merge could not complete. No changes were applied.");
    }
  };

  const ignoreMemory = async () => {
    if (!selected) return;
    if (!window.confirm("Ignore this memory so Synzept stops using it?")) return;
    setError(null);
    try {
      await api.ignoreMemory(selected.memory.id);
      await load();
    } catch {
      setError("Memory ignore failed. The memory is still active.");
    }
  };

  const deleteMemory = async () => {
    if (!selected) return;
    if (!window.confirm("Delete this memory permanently?")) return;
    setError(null);
    try {
      await api.deleteMemoryV2(selected.memory.id);
      await load();
    } catch {
      setError("Memory delete failed. The memory was not removed.");
    }
  };

  const explain = async (event: FormEvent) => {
    event.preventDefault();
    if (!messageId.trim()) return;
    setExplanationLoading(true);
    setExplanationError(null);
    try {
      setExplanation(await api.explainMemoryMessage(messageId.trim()));
    } catch {
      setExplanation(null);
      setExplanationError("Synzept could not explain that reply.");
    } finally {
      setExplanationLoading(false);
    }
  };

  return (
    <PageFrame eyebrow="Trust" title="Memory Explorer">
      <div className="grid min-h-0 gap-4 p-4 md:grid-cols-[360px_minmax(0,1fr)] md:p-6">
        <aside className="min-h-0 rounded-xl border border-border bg-white p-4 shadow-soft">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-muted" />
            <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search memory, project, or goal" />
          </div>
          <div className="mt-3 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => setIncludeIgnored((value) => !value)}
              className={cn("rounded-md border px-3 py-1.5 text-xs font-medium transition", includeIgnored ? "border-stone-900 bg-stone-900 text-white" : "border-border bg-white text-stone-700 hover:bg-stone-50")}
            >
              {includeIgnored ? "Showing ignored" : "Hide ignored"}
            </button>
            <span className="text-xs text-muted">{visibleItems.length} memories</span>
          </div>
          <div className="mt-4 max-h-[calc(100dvh-240px)] space-y-2 overflow-y-auto pr-1">
            {loading ? (
              <div className="space-y-2">
                <Skeleton className="h-20 rounded-lg" />
                <Skeleton className="h-20 rounded-lg" />
              </div>
            ) : visibleItems.length ? (
              visibleItems.map((item) => {
                const isSelected = item.memory.id === selected?.memory.id;
                return (
                  <button
                    key={item.memory.id}
                    type="button"
                    onClick={() => setSelectedId(item.memory.id)}
                    className={cn(
                      "w-full rounded-lg border px-3 py-3 text-left transition",
                      isSelected ? "border-stone-900 bg-stone-950 text-white shadow-soft" : "border-border bg-white hover:bg-stone-50",
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className={cn("truncate text-sm font-medium", isSelected ? "text-white" : "text-stone-950")}>
                        {item.memory.summary || item.memory.content.slice(0, 70)}
                      </p>
                      <span className={cn("rounded-full px-2 py-0.5 text-[10px] uppercase tracking-[0.14em]", isSelected ? "bg-white/10 text-stone-200" : "bg-stone-100 text-muted")}>{item.memory.source}</span>
                    </div>
                    <p className={cn("mt-1 line-clamp-2 text-xs leading-5", isSelected ? "text-stone-300" : "text-muted")}>
                      {item.memory.content}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px]">
                      <span className={cn("rounded-full px-2 py-0.5", isSelected ? "bg-white/10 text-stone-200" : "bg-stone-100 text-stone-700")}>Confidence {Math.round(item.memory.confidence * 100)}%</span>
                      <span className={cn("rounded-full px-2 py-0.5", isSelected ? "bg-white/10 text-stone-200" : "bg-stone-100 text-stone-700")}>Updated {formatDate(item.memory.updated_at)}</span>
                    </div>
                  </button>
                );
              })
            ) : (
              <EmptyState
                icon={<ShieldAlert className="h-5 w-5" />}
                title="No memories found"
                description="Synzept has no visible memories for the current filter. Try a different search or show ignored items."
              />
            )}
          </div>
        </aside>

        <main className="min-h-0 space-y-4 overflow-y-auto">
          <RecoveryBanner message={error} onRetry={load} />

          <section className="rounded-xl border border-border bg-white p-4 shadow-soft">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">AI explainability</p>
                <h2 className="mt-1 text-lg font-semibold text-stone-950">Why did Synzept say this?</h2>
                <p className="mt-1 text-sm text-muted">Paste a message ID from chat to inspect the memories, projects, open loops, and decisions behind a reply.</p>
              </div>
              <CircleHelp className="h-5 w-5 text-muted" />
            </div>
            <form onSubmit={explain} className="mt-4 flex flex-col gap-2 sm:flex-row">
              <Input value={messageId} onChange={(event) => setMessageId(event.target.value)} placeholder="Message ID" />
              <Button type="submit" variant="outline" disabled={explanationLoading}>
                {explanationLoading ? "Explaining..." : "Explain"}
              </Button>
            </form>
            {explanationError && <p className="mt-3 text-sm text-red-700">{explanationError}</p>}
            {explanation && (
              <div className="mt-4 space-y-3 rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm text-stone-700">
                <p className="leading-6">{explanation.explanation}</p>
                <ExplainBlock title="Memory used" items={explanation.memories_used.map((item) => item.summary || item.content)} />
                <ExplainBlock title="Projects used" items={explanation.projects_used.map((item) => item.title)} />
                <ExplainBlock title="Open loops used" items={explanation.open_loops_used.map((item) => item.title)} />
                <ExplainBlock title="Decisions used" items={explanation.decisions_used.map((item) => item.title)} />
              </div>
            )}
          </section>

          {!selected ? (
            <EmptyState
              icon={<PencilLine className="h-5 w-5" />}
              title="Select a memory"
              description="Choose a memory to inspect its source, confidence, connected projects, connected goals, and change history."
            />
          ) : (
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
              <section className="rounded-xl border border-border bg-white p-4 shadow-soft">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Memory</p>
                    <h2 className="mt-1 text-lg font-semibold text-stone-950">{selected.memory.summary || "Untitled memory"}</h2>
                    <p className="mt-1 text-sm text-muted">Source {selected.memory.source} · confidence {Math.round(selected.memory.confidence * 100)}% · last updated {formatDate(selected.memory.updated_at)}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" size="sm" onClick={ignoreMemory}>
                      <EyeOff className="mr-1.5 h-4 w-4" />
                      Ignore
                    </Button>
                    <Button type="button" variant="outline" size="sm" onClick={deleteMemory}>
                      <Trash2 className="mr-1.5 h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </div>

                <form onSubmit={saveMemory} className="mt-4 space-y-3">
                  <Textarea value={editContent} onChange={(event) => setEditContent(event.target.value)} rows={8} />
                  <div className="grid gap-3 md:grid-cols-3">
                    <Input value={editCategory} onChange={(event) => setEditCategory(event.target.value)} placeholder="Category" />
                    <Input value={editImportance} onChange={(event) => setEditImportance(event.target.value)} placeholder="Importance 0-1" />
                    <Input value={editReason} onChange={(event) => setEditReason(event.target.value)} placeholder="Why did this change?" />
                  </div>
                  <Button type="submit" size="sm">
                    <PencilLine className="mr-1.5 h-4 w-4" />
                    Save changes
                  </Button>
                </form>

                <div className="mt-5 grid gap-3 md:grid-cols-2">
                  <EntityCard title="Connected projects" items={selected.connected_projects.map((item) => item.title)} />
                  <EntityCard title="Connected goals" items={selected.connected_goals.map((item) => item.title)} />
                </div>

                <div className="mt-5 rounded-lg border border-stone-200 bg-stone-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-stone-950">
                    <Merge className="h-4 w-4 text-muted" />
                    Merge into this memory
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_auto]">
                    <select value={mergeSourceId} onChange={(event) => setMergeSourceId(event.target.value)} className="h-10 rounded-lg border border-border bg-white px-3 text-sm text-stone-800 outline-none">
                      <option value="">Choose source memory</option>
                      {visibleItems.filter((item) => item.memory.id !== selected.memory.id).map((item) => (
                        <option key={item.memory.id} value={item.memory.id}>
                          {item.memory.summary || item.memory.content.slice(0, 60)}
                        </option>
                      ))}
                    </select>
                    <Input value={mergeReason} onChange={(event) => setMergeReason(event.target.value)} placeholder="Reason for merge" />
                    <Button type="button" variant="outline" onClick={mergeMemory} disabled={!mergeSourceId}>
                      <Link2 className="mr-1.5 h-4 w-4" />
                      Merge
                    </Button>
                  </div>
                </div>
              </section>

              <aside className="space-y-4">
                <section className="rounded-xl border border-border bg-white p-4 shadow-soft">
                  <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Timeline</p>
                  <div className="mt-3 space-y-3">
                    {selected.timeline.length ? selected.timeline.map((event) => (
                      <article key={event.id} className="rounded-lg border border-stone-200 bg-stone-50 p-3">
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-medium text-stone-950">{event.action}</p>
                            <p className="mt-0.5 text-xs text-muted">{formatDate(event.created_at)} · {event.caused_by_type}</p>
                          </div>
                          <span className="rounded-full bg-white px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-muted">v{extractVersion(event.after) || extractVersion(event.before) || "?"}</span>
                        </div>
                        <p className="mt-2 text-sm leading-6 text-stone-700">{event.reason}</p>
                      </article>
                    )) : (
                      <EmptyState
                        icon={<CircleHelp className="h-5 w-5" />}
                        title="No timeline yet"
                        description="This memory has not changed since it was created, or its history has not been captured yet."
                        className="border-0 bg-transparent px-0 py-6 shadow-none"
                      />
                    )}
                  </div>
                </section>
              </aside>
            </div>
          )}
        </main>
      </div>
    </PageFrame>
  );
}

function EntityCard({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50 p-3">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{title}</p>
      <div className="mt-2 space-y-1.5">
        {items.length ? items.map((item) => <p key={item} className="rounded-md bg-white px-2.5 py-1.5 text-sm text-stone-700">{item}</p>) : <p className="text-sm text-muted">None linked</p>}
      </div>
    </div>
  );
}

function ExplainBlock({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{title}</p>
      <div className="mt-2 space-y-1.5">
        {items.slice(0, 4).map((item) => <p key={item} className="rounded-md bg-white px-2.5 py-1.5 text-sm text-stone-700">{item}</p>)}
      </div>
    </div>
  );
}

function formatDate(value: string) {
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  } catch {
    return value;
  }
}

function extractVersion(snapshot: Record<string, unknown>) {
  const value = snapshot.version;
  if (typeof value === "number" || typeof value === "string") return value;
  return "";
}
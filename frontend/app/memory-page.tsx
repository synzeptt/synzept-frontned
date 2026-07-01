"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Check, Clock3, Edit3, Lightbulb, Plus, Save, Sparkles, Trash2, X } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, type MemoryExplorerItem, type MemoryTrustRecord } from "@/lib/api";
import { cn } from "@/lib/cn";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CATEGORY_OPTIONS = [
  { id: "personal", label: "Personal" },
  { id: "goals", label: "Goals" },
  { id: "preferences", label: "Preferences" },
  { id: "projects", label: "Projects" },
  { id: "work", label: "Work" },
  { id: "learning", label: "Learning" },
  { id: "habits", label: "Habits" },
  { id: "current_focus", label: "Current Focus" },
];

const LEARNING_SUGGESTIONS = [
  { id: "bits", content: "You are preparing for BITS.", category: "learning" },
  { id: "simple-ui", content: "You prefer simple UI.", category: "preferences" },
  { id: "synzept", content: "You are building Synzept.", category: "projects" },
];

export function MemoryPage() {
  const [items, setItems] = useState<MemoryExplorerItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tellSynzept, setTellSynzept] = useState("");
  const [newCategory, setNewCategory] = useState("preferences");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [editCategory, setEditCategory] = useState("preferences");
  const [dismissedSuggestions, setDismissedSuggestions] = useState<Set<string>>(new Set());
  const [laterSuggestions, setLaterSuggestions] = useState<Set<string>>(new Set());
  const [autoSaveApproved, setAutoSaveApproved] = useState(false);
  const [profileDrafts, setProfileDrafts] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await api.listMemoryExplorer(false, false);
      setItems(rows);
    } catch {
      setError("Memory could not refresh. Your saved memories are still safe.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const memories = useMemo(
    () => items.map((item) => item.memory).filter((memory) => !memory.archived_at),
    [items],
  );

  const memoriesByCategory = useMemo(() => {
    const map = new Map<string, MemoryTrustRecord[]>();
    for (const memory of memories) {
      const key = normalizeCategory(memory.category || memory.memory_type);
      map.set(key, [...(map.get(key) || []), memory]);
    }
    return map;
  }, [memories]);

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const category of CATEGORY_OPTIONS) {
      next[category.id] = (memoriesByCategory.get(category.id) || []).map((memory) => memory.content).join("\n");
    }
    setProfileDrafts(next);
  }, [memoriesByCategory]);

  const visibleSuggestions = useMemo(
    () => LEARNING_SUGGESTIONS.filter((suggestion) => !dismissedSuggestions.has(suggestion.id) && !memories.some((memory) => memory.content.toLowerCase() === suggestion.content.toLowerCase())),
    [dismissedSuggestions, memories],
  );

  const createMemory = async (content: string, category = newCategory) => {
    const clean = content.trim();
    if (!clean) return;
    setSaving(true);
    setError(null);
    try {
      await api.createMemory({
        content: clean,
        category,
        memory_type: category,
        importance: 0.7,
        project_id: null,
        pinned: false,
        archived: false,
      });
      setTellSynzept("");
      await load();
    } catch {
      setError("Synzept could not remember that yet. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const submitTellSynzept = async (event: FormEvent) => {
    event.preventDefault();
    await createMemory(tellSynzept);
  };

  const startEdit = (memory: MemoryTrustRecord) => {
    setEditingId(memory.id);
    setEditDraft(memory.content);
    setEditCategory(normalizeCategory(memory.category || memory.memory_type));
  };

  const saveEdit = async (memory: MemoryTrustRecord) => {
    const clean = editDraft.trim();
    if (!clean) return;
    setSaving(true);
    setError(null);
    try {
      await api.updateMemoryV2(memory.id, {
        content: clean,
        category: editCategory,
        importance: memory.importance,
        reason: "User edited this memory.",
      });
      setEditingId(null);
      await load();
    } catch {
      setError("That memory could not be updated.");
    } finally {
      setSaving(false);
    }
  };

  const deleteMemory = async (memory: MemoryTrustRecord) => {
    if (!window.confirm("Delete this memory?")) return;
    setSaving(true);
    setError(null);
    try {
      await api.deleteMemoryV2(memory.id);
      await load();
    } catch {
      setError("That memory could not be deleted.");
    } finally {
      setSaving(false);
    }
  };

  const approveSuggestion = async (suggestion: (typeof LEARNING_SUGGESTIONS)[number]) => {
    await createMemory(suggestion.content, suggestion.category);
    setDismissedSuggestions((current) => new Set([...current, suggestion.id]));
  };

  const saveProfileSection = async (category: string) => {
    const content = (profileDrafts[category] || "").trim();
    const existing = memoriesByCategory.get(category)?.[0];
    setSaving(true);
    setError(null);
    try {
      if (existing) {
        await api.updateMemoryV2(existing.id, {
          content,
          category,
          importance: existing.importance,
          reason: "User edited About You.",
        });
      } else if (content) {
        await api.createMemory({
          content,
          category,
          memory_type: category,
          importance: 0.65,
          project_id: null,
          pinned: false,
          archived: false,
        });
      }
      await load();
    } catch {
      setError("That section could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageFrame eyebrow="Synzept Knows You" title="What Synzept knows about you">
      <div className="min-h-full bg-[#f7f6f2] px-4 py-5 text-stone-950 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl space-y-6">
          <RecoveryBanner message={error} onRetry={load} />

          <section className="rounded-lg bg-white p-5 shadow-[0_14px_40px_rgba(28,25,23,0.05)] ring-1 ring-stone-200/80 sm:p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Tell Synzept</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-stone-950">Build the relationship directly.</h2>
              </div>
              <span className="rounded-full bg-[#eef4ef] px-3 py-1 text-xs font-medium text-[#31563d]">You stay in control</span>
            </div>
            <form onSubmit={submitTellSynzept} className="mt-5 space-y-3">
              <Textarea
                value={tellSynzept}
                onChange={(event) => setTellSynzept(event.target.value)}
                rows={6}
                placeholder="Tell Synzept anything you want it to remember..."
                className="min-h-40 rounded-lg border-stone-200 bg-[#fbfaf7] text-base leading-7"
              />
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <select value={newCategory} onChange={(event) => setNewCategory(event.target.value)} className="h-10 rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none">
                  {CATEGORY_OPTIONS.map((category) => <option key={category.id} value={category.id}>{category.label}</option>)}
                </select>
                <button type="submit" disabled={saving || !tellSynzept.trim()} className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-stone-950 px-4 text-sm font-semibold text-white transition hover:bg-stone-800 disabled:bg-stone-200 disabled:text-stone-500">
                  <Plus className="h-4 w-4" />
                  Remember
                </button>
              </div>
            </form>
          </section>

          <section>
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Things Synzept Knows About You</p>
                <h2 className="mt-1 text-xl font-semibold text-stone-950">{memories.length} saved memories</h2>
              </div>
            </div>
            {loading ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <Skeleton className="h-36 rounded-lg" />
                <Skeleton className="h-36 rounded-lg" />
                <Skeleton className="h-36 rounded-lg" />
              </div>
            ) : memories.length ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {memories.map((memory) => (
                  <article key={memory.id} className="rounded-lg bg-white p-4 shadow-[0_10px_30px_rgba(28,25,23,0.04)] ring-1 ring-stone-200/80">
                    {editingId === memory.id ? (
                      <div className="space-y-3">
                        <Textarea value={editDraft} onChange={(event) => setEditDraft(event.target.value)} rows={5} className="rounded-lg" />
                        <select value={editCategory} onChange={(event) => setEditCategory(event.target.value)} className="h-9 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-700 outline-none">
                          {CATEGORY_OPTIONS.map((category) => <option key={category.id} value={category.id}>{category.label}</option>)}
                        </select>
                        <div className="flex gap-2">
                          <IconButton label="Save memory" onClick={() => saveEdit(memory)}><Save className="h-4 w-4" /></IconButton>
                          <IconButton label="Cancel edit" onClick={() => setEditingId(null)}><X className="h-4 w-4" /></IconButton>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-start gap-3">
                          <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#3f5f4a]" />
                          <p className="min-h-16 flex-1 text-sm leading-6 text-stone-800">{memory.content}</p>
                        </div>
                        <div className="mt-4 flex items-center justify-between gap-2">
                          <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-600">{labelForCategory(memory.category || memory.memory_type)}</span>
                          <div className="flex gap-1">
                            <IconButton label="Edit memory" onClick={() => startEdit(memory)}><Edit3 className="h-4 w-4" /></IconButton>
                            <IconButton label="Delete memory" danger onClick={() => deleteMemory(memory)}><Trash2 className="h-4 w-4" /></IconButton>
                          </div>
                        </div>
                      </>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-dashed border-stone-300 bg-white px-5 py-8 text-center">
                <Sparkles className="mx-auto h-6 w-6 text-stone-400" />
                <p className="mt-3 text-sm font-medium text-stone-950">No memories yet</p>
                <p className="mt-1 text-sm text-stone-500">Tell Synzept one preference, goal, project, or fact to begin.</p>
              </div>
            )}
          </section>

          <section className="rounded-lg bg-white p-5 ring-1 ring-stone-200/80 sm:p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">Synzept Learned</p>
                <h2 className="mt-2 text-xl font-semibold text-stone-950">New learnings wait for your approval.</h2>
              </div>
              <label className="flex items-center gap-2 text-sm text-stone-700">
                <input type="checkbox" checked={autoSaveApproved} onChange={(event) => setAutoSaveApproved(event.target.checked)} className="h-4 w-4 rounded border-stone-300" />
                Automatically save approved learnings
              </label>
            </div>
            <div className="mt-5 grid gap-3 lg:grid-cols-3">
              {visibleSuggestions.length ? visibleSuggestions.map((suggestion) => (
                <article key={suggestion.id} className={cn("rounded-lg border p-4", laterSuggestions.has(suggestion.id) ? "border-stone-200 bg-stone-50" : "border-[#cbd8ce] bg-[#f5faf6]")}>
                  <div className="flex items-start gap-3">
                    <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-[#3f5f4a]" />
                    <div>
                      <p className="text-sm font-semibold text-stone-950">Synzept learned something.</p>
                      <p className="mt-2 text-sm leading-6 text-stone-700">{suggestion.content}</p>
                    </div>
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <SmallButton onClick={() => approveSuggestion(suggestion)}>Approve</SmallButton>
                    <SmallButton variant="light" onClick={() => setDismissedSuggestions((current) => new Set([...current, suggestion.id]))}>Dismiss</SmallButton>
                    <SmallButton variant="light" onClick={() => setLaterSuggestions((current) => new Set([...current, suggestion.id]))}><Clock3 className="h-3.5 w-3.5" />Later</SmallButton>
                  </div>
                </article>
              )) : (
                <div className="rounded-lg border border-dashed border-stone-300 bg-stone-50 p-5 text-sm leading-6 text-stone-600 lg:col-span-3">
                  New long-term learnings from chat will appear here before Synzept saves them.
                </div>
              )}
            </div>
          </section>

          <section>
            <div className="mb-3">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-stone-500">About You</p>
              <h2 className="mt-1 text-xl font-semibold text-stone-950">The single source of truth for your context.</h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {CATEGORY_OPTIONS.map((category) => (
                <article key={category.id} className="rounded-lg bg-white p-4 ring-1 ring-stone-200/80">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-stone-950">{category.label}</h3>
                    <button type="button" onClick={() => saveProfileSection(category.id)} disabled={saving} className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-stone-200 px-2.5 text-xs font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-50">
                      <Save className="h-3.5 w-3.5" />
                      Save
                    </button>
                  </div>
                  <Textarea
                    value={profileDrafts[category.id] || ""}
                    onChange={(event) => setProfileDrafts((current) => ({ ...current, [category.id]: event.target.value }))}
                    rows={5}
                    placeholder={`Add ${category.label.toLowerCase()} context...`}
                    className="rounded-lg bg-[#fbfaf7]"
                  />
                </article>
              ))}
            </div>
          </section>
        </div>
      </div>
    </PageFrame>
  );
}

function IconButton({ label, danger, onClick, children }: { label: string; danger?: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-label={label} title={label} className={cn("grid h-8 w-8 place-items-center rounded-lg text-stone-500 hover:bg-stone-100 hover:text-stone-950", danger && "hover:bg-rose-50 hover:text-rose-600")}>
      {children}
    </button>
  );
}

function SmallButton({ children, variant = "dark", onClick }: { children: React.ReactNode; variant?: "dark" | "light"; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className={cn("inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold transition", variant === "dark" ? "bg-stone-950 text-white hover:bg-stone-800" : "border border-stone-200 bg-white text-stone-700 hover:bg-stone-50")}>
      {children}
    </button>
  );
}

function normalizeCategory(value?: string | null) {
  const normalized = (value || "personal").toLowerCase().replace(/[-\s]+/g, "_");
  if (normalized === "priorities") return "current_focus";
  if (normalized === "identity" || normalized === "relationships") return "personal";
  if (normalized === "long_term_plans") return "learning";
  return CATEGORY_OPTIONS.some((category) => category.id === normalized) ? normalized : "personal";
}

function labelForCategory(value?: string | null) {
  const normalized = normalizeCategory(value);
  return CATEGORY_OPTIONS.find((category) => category.id === normalized)?.label || "Personal";
}

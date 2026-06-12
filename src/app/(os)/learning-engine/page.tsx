"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Edit3, Lightbulb, RefreshCw, Search, X } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { ProGate } from "@/components/pro/pro-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, type LearningEngine, type LearningSuggestion } from "@/lib/api";

export default function LearningEnginePage() {
  const [engine, setEngine] = useState<LearningEngine | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [editing, setEditing] = useState<LearningSuggestion | null>(null);
  const [draftTitle, setDraftTitle] = useState("");
  const [draftDescription, setDraftDescription] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const pending = useMemo(() => (engine?.suggestions || []).filter((item) => item.status === "pending"), [engine]);
  const accepted = useMemo(() => (engine?.suggestions || []).filter((item) => item.status === "accepted"), [engine]);
  const ignored = useMemo(() => (engine?.suggestions || []).filter((item) => item.status === "ignored"), [engine]);

  const load = useCallback(async () => {
    setIsLoading(true);
    setMessage(null);
    try {
      setEngine(await api.getLearningEngine());
    } catch {
      setMessage("Learning suggestions could not load. Your profile was not changed.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const analyze = async () => {
    setIsAnalyzing(true);
    setMessage(null);
    try {
      const result = await api.analyzeLearning();
      setEngine({ observations: engine?.observations || [], suggestions: result.suggestions });
      setMessage(result.suggestionsCreated ? `${result.suggestionsCreated} new suggestion${result.suggestionsCreated === 1 ? "" : "s"} ready for review.` : "No new suggestions found.");
      await load();
    } catch {
      setMessage("Analysis could not run. Nothing was saved to your profile.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const accept = async (item: LearningSuggestion) => {
    setMessage(null);
    try {
      await api.acceptLearningSuggestion(item.id);
      setMessage("Accepted. Synzept will use this approved learning in continuity features.");
      await load();
    } catch {
      setMessage("That suggestion could not be accepted.");
    }
  };

  const ignore = async (item: LearningSuggestion) => {
    setMessage(null);
    try {
      await api.ignoreLearningSuggestion(item.id);
      setMessage("Ignored. Synzept will not use that suggestion.");
      await load();
    } catch {
      setMessage("That suggestion could not be ignored.");
    }
  };

  const startEdit = (item: LearningSuggestion) => {
    setEditing(item);
    setDraftTitle(item.title);
    setDraftDescription(item.description);
  };

  const saveEdit = async () => {
    if (!editing) return;
    setMessage(null);
    try {
      await api.editLearningSuggestion(editing.id, {
        title: draftTitle.trim(),
        description: draftDescription.trim(),
      });
      setEditing(null);
      setMessage("Edited. Review the revised suggestion before accepting it.");
      await load();
    } catch {
      setMessage("That suggestion could not be edited.");
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader label="Transparent learning" title="Learning Suggestions" />

      <ProGate feature="Learning Suggestions" description="Transparent learning is a Synzept Pro system that suggests insights, explains why, and waits for your approval before updating what Synzept knows.">
      <div className="mx-auto max-w-5xl space-y-5 px-4 py-5 md:px-8">
        {message && <p className="rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700">{message}</p>}

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
            <div>
              <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
                <Lightbulb className="h-4 w-4 text-muted" />
                Observe, suggest, then ask.
              </p>
              <p className="mt-1 text-sm leading-6 text-muted">
                Synzept can analyze workspace activity, but accepted learnings are the only ones used in your profile and continuity systems.
              </p>
            </div>
            <Button onClick={analyze} disabled={isAnalyzing}>
              <RefreshCw className={`mr-1.5 h-4 w-4 ${isAnalyzing ? "animate-spin" : ""}`} />
              {isAnalyzing ? "Analyzing..." : "Analyze Activity"}
            </Button>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <Metric label="Pending Review" value={pending.length} />
            <Metric label="Accepted" value={accepted.length} />
            <Metric label="Ignored" value={ignored.length} />
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <SectionTitle title="Review Suggestions" description="Accept, edit, or ignore every learning before Synzept stores it as part of its understanding." />
          <div className="mt-4 space-y-3">
            {isLoading && <p className="text-sm text-muted">Loading suggestions...</p>}
            {!isLoading && pending.map((item) => (
              <SuggestionCard key={item.id} item={item} onAccept={accept} onEdit={startEdit} onIgnore={ignore} />
            ))}
            {!isLoading && !pending.length && (
              <p className="rounded-md bg-stone-50 px-3 py-3 text-sm text-muted">No suggestions need review. Run analysis after adding projects, notes, tasks, or timeline activity.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <SectionTitle title="Approved Learnings" description="These are the only learning suggestions Synzept can use in Knows You, Daily Brief, Continuity Assistant, and Project Intelligence." />
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {accepted.slice(0, 6).map((item) => (
              <div key={item.id} className="rounded-md bg-stone-50 px-3 py-3">
                <p className="text-sm font-medium text-stone-950">{item.title}</p>
                <p className="mt-1 text-xs leading-5 text-muted">{item.description}</p>
              </div>
            ))}
            {!accepted.length && <p className="text-sm text-muted">Accepted learnings will appear here.</p>}
          </div>
        </section>
      </div>
      </ProGate>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/20 px-4">
          <div className="w-full max-w-xl rounded-lg border border-border bg-white p-5 shadow-panel">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-stone-950">Edit learning suggestion</h2>
                <p className="mt-1 text-sm text-muted">Revise what Synzept should learn before accepting it.</p>
              </div>
              <button type="button" onClick={() => setEditing(null)} className="rounded-md p-2 text-muted hover:bg-stone-50 hover:text-stone-950" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="mt-4 space-y-3">
              <input
                value={draftTitle}
                onChange={(event) => setDraftTitle(event.target.value)}
                className="h-10 w-full rounded-lg border border-border bg-white px-3.5 text-sm text-stone-900 outline-none transition focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
              />
              <Textarea value={draftDescription} onChange={(event) => setDraftDescription(event.target.value)} className="min-h-28" />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
              <Button onClick={saveEdit} disabled={!draftTitle.trim() || !draftDescription.trim()}>
                <Check className="mr-1.5 h-4 w-4" />
                Save
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SuggestionCard({
  item,
  onAccept,
  onEdit,
  onIgnore,
}: {
  item: LearningSuggestion;
  onAccept: (item: LearningSuggestion) => void;
  onEdit: (item: LearningSuggestion) => void;
  onIgnore: (item: LearningSuggestion) => void;
}) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-stone-950">{item.title}</p>
            <Badge variant="muted">{Math.round((item.confidence || 0.5) * 100)}% confidence</Badge>
          </div>
          <p className="mt-2 text-sm leading-6 text-muted">{item.description}</p>
          <div className="mt-3 rounded-md bg-stone-50 px-3 py-2">
            <p className="flex items-center gap-2 text-xs font-medium text-stone-700">
              <Search className="h-3.5 w-3.5" />
              Why Synzept believes this
            </p>
            <p className="mt-1 text-xs leading-5 text-muted">{item.sourceExplanation || item.description}</p>
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button size="sm" onClick={() => onAccept(item)}>
            <Check className="mr-1.5 h-4 w-4" />
            Accept
          </Button>
          <Button size="sm" variant="outline" onClick={() => onEdit(item)}>
            <Edit3 className="mr-1.5 h-4 w-4" />
            Edit
          </Button>
          <Button size="sm" variant="outline" onClick={() => onIgnore(item)}>
            <X className="mr-1.5 h-4 w-4" />
            Ignore
          </Button>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-3">
      <p className="text-2xl font-semibold text-stone-950">{value}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </div>
  );
}

function SectionTitle({ title, description }: { title: string; description?: string }) {
  return (
    <div>
      <p className="text-sm font-semibold text-stone-950">{title}</p>
      {description && <p className="mt-1 text-sm leading-6 text-muted">{description}</p>}
    </div>
  );
}

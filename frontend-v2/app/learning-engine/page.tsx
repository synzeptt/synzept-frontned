"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Check, Pencil, Plus, Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type LearningObservation, type LearningSuggestion } from "@/lib/api";

export default function LearningEnginePage() {
  const [observations, setObservations] = useState<LearningObservation[]>([]);
  const [suggestions, setSuggestions] = useState<LearningSuggestion[]>([]);
  const [content, setContent] = useState("");
  const [source, setSource] = useState("manual");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<LearningSuggestion | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getLearningEngine()
      .then((data) => {
        setObservations(data.observations);
        setSuggestions(data.suggestions);
      })
      .catch(() => setError("Learning Engine could not load. No understanding was changed."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const pendingSuggestions = useMemo(() => suggestions.filter((item) => item.status === "pending"), [suggestions]);

  const createObservation = async (event: FormEvent) => {
    event.preventDefault();
    if (!content.trim()) return;
    try {
      const created = await api.createLearningObservation({ content: content.trim(), source: source.trim() || "manual" });
      setObservations([created, ...observations]);
      setContent("");
    } catch {
      setError("Observation could not be saved.");
    }
  };

  const analyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const result = await api.analyzeLearning();
      setSuggestions(result.suggestions);
      await load();
    } catch {
      setError("Analysis could not complete. Nothing was stored as understanding.");
    } finally {
      setAnalyzing(false);
    }
  };

  const accept = async (suggestion: LearningSuggestion) => {
    const updated = await api.acceptLearningSuggestion(suggestion.id);
    setSuggestions(suggestions.map((item) => (item.id === updated.id ? updated : item)));
  };

  const ignore = async (suggestion: LearningSuggestion) => {
    const updated = await api.ignoreLearningSuggestion(suggestion.id);
    setSuggestions(suggestions.map((item) => (item.id === updated.id ? updated : item)));
  };

  const saveEdit = async (suggestion: LearningSuggestion) => {
    const updated = await api.editLearningSuggestion(suggestion.id, {
      title: suggestion.title,
      description: suggestion.description,
    });
    setSuggestions(suggestions.map((item) => (item.id === updated.id ? updated : item)));
    setEditing(null);
  };

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-10">
        <header className="mb-6">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Phase 4</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Learning Engine</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
            Observe, analyze, suggest, then wait for approval. Learned understanding is never stored automatically.
          </p>
        </header>

        <RecoveryBanner message={error} onRetry={load} />

        <section className="mb-5 rounded-lg border border-border bg-white p-4 sm:p-5">
          <p className="text-sm font-medium text-stone-950">Add observation</p>
          <form onSubmit={createObservation} className="mt-3 grid gap-3 md:grid-cols-[160px_1fr_auto]">
            <Input value={source} onChange={(event) => setSource(event.target.value)} placeholder="Source" />
            <Input value={content} onChange={(event) => setContent(event.target.value)} placeholder="Signal Synzept should analyze" />
            <Button type="submit" size="sm">
              <Plus className="mr-1.5 h-4 w-4" />
              Observe
            </Button>
          </form>
          <Button className="mt-3" size="sm" variant="outline" onClick={analyze} disabled={analyzing}>
            <Search className="mr-1.5 h-4 w-4" />
            {analyzing ? "Analyzing..." : "Analyze Observations"}
          </Button>
        </section>

        {loading ? (
          <Skeleton className="h-44 rounded-md" />
        ) : (
          <div className="grid gap-5 lg:grid-cols-2">
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Observations</h2>
              <div className="mt-3 space-y-2">
                {observations.map((item) => (
                  <div key={item.id} className="rounded-md bg-stone-50 px-3 py-2">
                    <p className="text-sm text-stone-800">{item.content}</p>
                    <p className="mt-1 text-xs text-muted">{item.source} / {item.status}</p>
                  </div>
                ))}
                {!observations.length && <p className="text-sm text-muted">No observations yet.</p>}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Suggested Understanding</h2>
              <div className="mt-3 space-y-3">
                {pendingSuggestions.map((suggestion) => {
                  const current = editing?.id === suggestion.id ? editing : suggestion;
                  return (
                    <article key={suggestion.id} className="rounded-md border border-border bg-stone-50 p-3">
                      {editing?.id === suggestion.id ? (
                        <div className="space-y-2">
                          <Input value={current.title} onChange={(event) => setEditing({ ...current, title: event.target.value })} />
                          <textarea
                            value={current.description}
                            onChange={(event) => setEditing({ ...current, description: event.target.value })}
                            className="min-h-20 w-full resize-y rounded-lg border border-border bg-white px-3 py-2 text-sm outline-none"
                          />
                        </div>
                      ) : (
                        <>
                          <p className="text-sm font-medium text-stone-950">{suggestion.title}</p>
                          <p className="mt-1 text-sm leading-6 text-stone-600">{suggestion.description}</p>
                        </>
                      )}
                      <div className="mt-3 flex flex-wrap gap-2">
                        {editing?.id === suggestion.id ? (
                          <>
                            <Button size="sm" onClick={() => saveEdit(current)}>Save edit</Button>
                            <Button size="sm" variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
                          </>
                        ) : (
                          <>
                            <Button size="sm" onClick={() => accept(suggestion)}><Check className="mr-1.5 h-4 w-4" />Accept</Button>
                            <Button size="sm" variant="outline" onClick={() => setEditing(suggestion)}><Pencil className="mr-1.5 h-4 w-4" />Edit</Button>
                            <Button size="sm" variant="ghost" onClick={() => ignore(suggestion)}><X className="mr-1.5 h-4 w-4" />Ignore</Button>
                          </>
                        )}
                      </div>
                    </article>
                  );
                })}
                {!pendingSuggestions.length && <p className="text-sm text-muted">No pending suggestions. Nothing has been stored automatically.</p>}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

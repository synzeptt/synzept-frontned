"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { CalendarDays, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type TimelineEvent } from "@/lib/api";

const eventTypes: TimelineEvent["eventType"][] = ["milestone", "decision", "learning", "achievement", "progress"];

export default function TimelinePage() {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const today = new Date().toISOString().slice(0, 10);
  const [draft, setDraft] = useState({
    eventType: "progress" as TimelineEvent["eventType"],
    title: "",
    description: "",
    eventDate: today,
    importance: 0.5,
  });

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .listTimelineEvents()
      .then(setEvents)
      .catch(() => setError("Timeline could not load. Your meaningful history is still safe."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const grouped = useMemo(() => {
    const byDate = new Map<string, TimelineEvent[]>();
    for (const event of events) {
      const date = event.eventDate;
      byDate.set(date, [...(byDate.get(date) || []), event]);
    }
    return [...byDate.entries()].sort(([a], [b]) => b.localeCompare(a));
  }, [events]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.title.trim()) return;
    try {
      const created = await api.createTimelineEvent({
        eventType: draft.eventType,
        title: draft.title.trim(),
        description: draft.description.trim(),
        eventDate: draft.eventDate,
        importance: draft.importance,
      });
      setEvents([created, ...events]);
      setDraft({ eventType: "progress", title: "", description: "", eventDate: today, importance: 0.5 });
    } catch {
      setError("Timeline event could not be saved.");
    }
  };

  const remove = async (event: TimelineEvent) => {
    await api.deleteTimelineEvent(event.id);
    setEvents(events.filter((item) => item.id !== event.id));
  };

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 md:py-10">
        <header className="mb-6">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Phase 3</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Timeline</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
            Meaningful history only: milestones, decisions, learning, achievements, and progress.
          </p>
        </header>

        <RecoveryBanner message={error} onRetry={load} />

        <form onSubmit={create} className="mb-5 rounded-lg border border-border bg-white p-4 sm:p-5">
          <div className="grid gap-3 md:grid-cols-[180px_1fr_160px]">
            <select
              value={draft.eventType}
              onChange={(event) => setDraft({ ...draft, eventType: event.target.value as TimelineEvent["eventType"] })}
              className="h-10 rounded-lg border border-border bg-white px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
            >
              {eventTypes.map((type) => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
            <Input value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} placeholder="What meaningfully happened?" />
            <Input type="date" value={draft.eventDate} onChange={(event) => setDraft({ ...draft, eventDate: event.target.value })} />
          </div>
          <textarea
            value={draft.description}
            onChange={(event) => setDraft({ ...draft, description: event.target.value })}
            placeholder="Why this matters"
            className="mt-3 min-h-24 w-full resize-y rounded-lg border border-border bg-white px-3 py-2 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
          />
          <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <label className="flex items-center gap-3 text-xs text-muted">
              Importance
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={draft.importance}
                onChange={(event) => setDraft({ ...draft, importance: Number(event.target.value) })}
              />
              {Math.round(draft.importance * 100)}%
            </label>
            <Button size="sm" type="submit">
              <Plus className="mr-1.5 h-4 w-4" />
              Add Event
            </Button>
          </div>
        </form>

        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-28 rounded-md" />
            <Skeleton className="h-28 rounded-md" />
          </div>
        ) : (
          <div className="space-y-5">
            {grouped.map(([date, items]) => (
              <section key={date} className="rounded-lg border border-border bg-white p-4 sm:p-5">
                <div className="mb-4 flex items-center gap-2 text-sm font-medium text-stone-950">
                  <CalendarDays className="h-4 w-4 text-muted" />
                  {new Date(`${date}T00:00:00`).toLocaleDateString()}
                </div>
                <div className="space-y-3">
                  {items.map((event) => (
                    <article key={event.id} className="rounded-md border border-border bg-stone-50 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{event.eventType}</p>
                          <h2 className="mt-1 text-sm font-semibold text-stone-950">{event.title}</h2>
                          {event.description && <p className="mt-1 text-sm leading-6 text-stone-600">{event.description}</p>}
                        </div>
                        <button
                          type="button"
                          onClick={() => remove(event)}
                          className="rounded-md p-2 text-stone-400 hover:bg-white hover:text-red-700"
                          aria-label={`Delete ${event.title}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ))}
            {!events.length && (
              <section className="rounded-lg border border-border bg-white p-6 text-sm text-stone-500">
                Add the first meaningful event to explain how you got here.
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

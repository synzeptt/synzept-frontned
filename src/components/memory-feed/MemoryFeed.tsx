"use client";

import { useMemo, useState } from "react";
import { RefreshCcw, Search, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { memoryFeedMock } from "@/lib/memory-feed/mock-data";
import { rankMemoryFeedCards } from "@/lib/memory-feed/ranking";
import type { MemoryFeedCard, MemoryFeedFilter } from "@/lib/memory-feed/types";
import { cn } from "@/lib/cn";
import { MemoryFeedCard as FeedCard } from "./MemoryFeedCard";

const filters: { label: string; value: MemoryFeedFilter }[] = [
  { label: "All", value: "all" },
  { label: "Open Loops", value: "open_loop" },
  { label: "Decisions", value: "recent_decision" },
  { label: "Progress", value: "mission_progress" },
  { label: "People", value: "relationship_reminder" },
  { label: "Insights", value: "ai_insight" },
];

function formatRefreshTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function MemoryFeed() {
  const [cards, setCards] = useState<MemoryFeedCard[]>(memoryFeedMock.cards);
  const [filter, setFilter] = useState<MemoryFeedFilter>("all");
  const [query, setQuery] = useState("");
  const [explanations, setExplanations] = useState<Set<string>>(new Set());
  const [activePrompt, setActivePrompt] = useState<string | null>(null);
  const [refreshNote, setRefreshNote] = useState(memoryFeedMock.refreshLabel);

  const visibleCards = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return rankMemoryFeedCards(cards, 7).filter((card) => {
      const matchesFilter = filter === "all" || card.type === filter;
      const searchable = [card.title, card.summary, card.detail, card.project, card.relatedPerson, ...card.tags]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesFilter && (!normalizedQuery || searchable.includes(normalizedQuery));
    });
  }, [cards, filter, query]);

  const updateCard = (id: string, update: (card: MemoryFeedCard) => MemoryFeedCard) => {
    setCards((currentCards) => currentCards.map((card) => (card.id === id ? update(card) : card)));
  };

  const handleComplete = (id: string) => updateCard(id, (card) => ({ ...card, status: "completed" }));
  const handleSnooze = (id: string) => updateCard(id, (card) => ({ ...card, status: "snoozed" }));
  const handleArchive = (id: string) => updateCard(id, (card) => ({ ...card, status: "archived" }));
  const handlePin = (id: string) => updateCard(id, (card) => ({ ...card, pinned: !card.pinned }));

  const handleExplain = (id: string) => {
    setExplanations((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleRefresh = () => {
    setCards(memoryFeedMock.cards);
    setRefreshNote(`Refreshed from mock feed at ${formatRefreshTime(memoryFeedMock.generatedAt)}`);
  };

  return (
    <div className="min-h-full bg-stone-50 text-stone-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Memory Feed</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal text-stone-950 sm:text-4xl">What to remember today</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
                A ranked daily feed of important memories, recent decisions, open loops, progress, reminders, opportunities, and next actions.
              </p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div className="rounded-md border border-border bg-surface px-3 py-2 text-xs text-muted-foreground">
                Next refresh: {formatRefreshTime(memoryFeedMock.nextRefreshAt)}
              </div>
              <Button variant="outline" onClick={handleRefresh}>
                <RefreshCcw className="mr-2 h-4 w-4" />
                Refresh
              </Button>
            </div>
          </div>
        </section>

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
          <main className="space-y-4">
            <div className="rounded-lg border border-border bg-white p-3 shadow-soft">
              <div className="flex flex-col gap-3 md:flex-row md:items-center">
                <label className="relative flex-1">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
                  <Input
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Search memories, projects, people, tags"
                    className="pl-9"
                  />
                </label>
                <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
                  <SlidersHorizontal className="h-4 w-4 shrink-0 text-muted" />
                  {filters.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => setFilter(item.value)}
                      className={cn(
                        "h-9 shrink-0 rounded-md px-3 text-sm font-medium transition",
                        filter === item.value ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-700 hover:bg-stone-200",
                      )}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="max-h-[calc(100vh-260px)] space-y-4 overflow-y-auto pr-1 scroll-smooth">
              {visibleCards.map((card) => (
                <FeedCard
                  key={card.id}
                  card={card}
                  explanationOpen={explanations.has(card.id)}
                  onComplete={handleComplete}
                  onSnooze={handleSnooze}
                  onPin={handlePin}
                  onArchive={handleArchive}
                  onAsk={setActivePrompt}
                  onExplain={handleExplain}
                />
              ))}
              {visibleCards.length === 0 && (
                <div className="rounded-lg border border-dashed border-border bg-white p-8 text-center text-sm text-muted-foreground">
                  No feed cards match this search and filter.
                </div>
              )}
            </div>
          </main>

          <aside className="space-y-4">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <p className="text-sm font-semibold text-stone-950">Ranking Model</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                Cards are scored from relevance, urgency, importance, recency, and feedback. Pinned cards stay visible; snoozed and archived cards leave today&apos;s feed.
              </p>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs text-stone-600">
                {["Relevance", "Urgency", "Importance", "Recency", "Feedback", "Pinned boost"].map((item) => (
                  <div key={item} className="rounded-md bg-stone-50 px-3 py-2">
                    {item}
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <p className="text-sm font-semibold text-stone-950">Daily Refresh</p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{refreshNote}</p>
            </section>

            {activePrompt && (
              <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
                <p className="text-sm font-semibold text-stone-950">Follow-up Question</p>
                <p className="mt-2 text-sm leading-6 text-stone-700">{activePrompt}</p>
                <Button className="mt-4 w-full" variant="outline" onClick={() => setActivePrompt(null)}>
                  Clear
                </Button>
              </section>
            )}
          </aside>
        </div>
      </div>
    </div>
  );
}

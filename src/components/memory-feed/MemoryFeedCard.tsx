"use client";

import {
  Archive,
  CheckCircle2,
  Clock3,
  HelpCircle,
  MessageCircleQuestion,
  Pin,
  PinOff,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { MemoryFeedCard as MemoryFeedCardType } from "@/lib/memory-feed/types";

const cardLabels: Record<MemoryFeedCardType["type"], string> = {
  important_memory: "Important Memory",
  recent_decision: "Recent Decision",
  open_loop: "Open Loop",
  mission_progress: "Mission Progress",
  relationship_reminder: "Relationship Reminder",
  opportunity: "Opportunity",
  ai_insight: "AI Insight",
  weekly_reflection: "Weekly Reflection",
  achievement: "Achievement",
  suggested_next_action: "Suggested Next Action",
};

const accentByType: Record<MemoryFeedCardType["type"], string> = {
  important_memory: "border-l-amber-500",
  recent_decision: "border-l-sky-500",
  open_loop: "border-l-rose-500",
  mission_progress: "border-l-emerald-500",
  relationship_reminder: "border-l-indigo-500",
  opportunity: "border-l-teal-500",
  ai_insight: "border-l-violet-500",
  weekly_reflection: "border-l-stone-500",
  achievement: "border-l-lime-600",
  suggested_next_action: "border-l-orange-500",
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export function MemoryFeedCard({
  card,
  explanationOpen,
  onComplete,
  onSnooze,
  onPin,
  onArchive,
  onAsk,
  onExplain,
}: {
  card: MemoryFeedCardType;
  explanationOpen: boolean;
  onComplete: (id: string) => void;
  onSnooze: (id: string) => void;
  onPin: (id: string) => void;
  onArchive: (id: string) => void;
  onAsk: (prompt: string) => void;
  onExplain: (id: string) => void;
}) {
  return (
    <article className={cn("rounded-lg border border-border border-l-4 bg-white p-4 shadow-soft", accentByType[card.type])}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="muted">{cardLabels[card.type]}</Badge>
            {card.pinned && <Badge variant="accent">Pinned</Badge>}
            {card.dueAt && <Badge className="bg-rose-50 text-rose-700">Due {formatTime(card.dueAt)}</Badge>}
          </div>
          <h2 className="mt-3 text-lg font-semibold leading-6 text-stone-950">{card.title}</h2>
        </div>
        <div className="flex items-center gap-1">
          <Button size="icon" variant="ghost" aria-label={card.pinned ? "Unpin card" : "Pin card"} title={card.pinned ? "Unpin" : "Pin"} onClick={() => onPin(card.id)}>
            {card.pinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
          </Button>
          <Button size="icon" variant="ghost" aria-label="Archive card" title="Archive" onClick={() => onArchive(card.id)}>
            <Archive className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <p className="mt-3 text-sm leading-6 text-stone-700">{card.summary}</p>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{card.detail}</p>

      <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
        <span>{formatTime(card.timestamp)}</span>
        <span aria-hidden="true">/</span>
        <span>{card.source}</span>
        {card.project && (
          <>
            <span aria-hidden="true">/</span>
            <span>{card.project}</span>
          </>
        )}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {card.tags.map((tag) => (
          <span key={tag} className="rounded-full bg-stone-50 px-2.5 py-1 text-xs text-stone-600">
            {tag}
          </span>
        ))}
      </div>

      {card.suggestedAction && (
        <div className="mt-4 rounded-md border border-border bg-surface px-3 py-2">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Suggested next action</p>
          <p className="mt-1 text-sm text-stone-700">{card.suggestedAction}</p>
        </div>
      )}

      {explanationOpen && (
        <div className="mt-4 rounded-md border border-border bg-white p-3">
          <p className="text-sm font-semibold text-stone-950">Why this appeared</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-5">
            {card.factors.map((factor) => (
              <div key={factor.label} className="rounded-md bg-stone-50 p-2">
                <p className="text-[11px] text-muted-foreground">{factor.label}</p>
                <p className="mt-1 text-sm font-semibold text-stone-900">{factor.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" onClick={() => onComplete(card.id)}>
          <CheckCircle2 className="mr-2 h-4 w-4" />
          Complete
        </Button>
        <Button size="sm" variant="outline" onClick={() => onSnooze(card.id)}>
          <Clock3 className="mr-2 h-4 w-4" />
          Snooze
        </Button>
        <Button size="sm" variant="outline" onClick={() => onAsk(card.followUpPrompt ?? `Tell me more about ${card.title}`)}>
          <MessageCircleQuestion className="mr-2 h-4 w-4" />
          Ask
        </Button>
        <Button size="sm" variant="ghost" onClick={() => onExplain(card.id)}>
          <HelpCircle className="mr-2 h-4 w-4" />
          Why
        </Button>
      </div>
    </article>
  );
}

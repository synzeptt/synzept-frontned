"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export type DailyOSRecommendationAction = {
  id: string;
  label: string;
  prompt: string;
};

export type DailyOSRecommendation = {
  id: string;
  title: string;
  reason: string;
  benefit: string;
  actionLabel: string;
  whyThisExists?: string[];
  memoriesUsed?: string[];
  connectedApps?: string[];
  confidence?: string;
  updatedAt?: string;
  actions?: DailyOSRecommendationAction[];
};

export type RecommendationsProps = {
  items: DailyOSRecommendation[];
  onAction?: (id: string, actionId?: string) => Promise<void> | void;
};

export function Recommendations({ items, onAction }: RecommendationsProps) {
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [completedAction, setCompletedAction] = useState<string | null>(null);

  const handleAction = async (itemId: string, actionId?: string) => {
    const key = actionId ? `${itemId}:${actionId}` : itemId;
    setBusyAction(key);
    setCompletedAction(null);
    try {
      await onAction?.(itemId, actionId);
      setCompletedAction(key);
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <section className="rounded-[28px] bg-white p-6 shadow-soft md:p-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-400">Recommendations</p>
        <h2 className="mt-3 text-2xl font-semibold text-stone-950">What to do next</h2>
      </div>
      <div className="mt-6 grid gap-4">
        {items.map((item) => (
          <article key={item.id} className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-2">
                <p className="text-base font-semibold text-stone-950">{item.title}</p>
                <p className="text-sm leading-6 text-stone-700">{item.reason}</p>
                <p className="text-sm font-medium text-stone-900">Expected benefit: {item.benefit}</p>
                <div className="space-y-2 pt-2 text-sm leading-6 text-stone-600">
                  {item.whyThisExists?.length ? (
                    <div>
                      <p className="font-medium text-stone-800">Why this exists</p>
                      <ul className="mt-1 list-disc pl-5">
                        {item.whyThisExists.map((entry) => <li key={entry}>{entry}</li>)}
                      </ul>
                    </div>
                  ) : null}
                  {item.memoriesUsed?.length ? (
                    <div>
                      <p className="font-medium text-stone-800">Memories used</p>
                      <p className="mt-1">{item.memoriesUsed.join(" • ")}</p>
                    </div>
                  ) : null}
                  {item.connectedApps?.length ? (
                    <div>
                      <p className="font-medium text-stone-800">Connected apps</p>
                      <p className="mt-1">{item.connectedApps.join(" • ")}</p>
                    </div>
                  ) : null}
                  {(item.confidence || item.updatedAt) ? (
                    <div className="flex flex-wrap gap-4 text-xs uppercase tracking-[0.16em] text-stone-400">
                      {item.confidence ? <span>Confidence {item.confidence}</span> : null}
                      {item.updatedAt ? <span>Updated {item.updatedAt}</span> : null}
                    </div>
                  ) : null}
                </div>
              </div>
              <div className="flex flex-col gap-2 sm:items-end">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="w-full justify-center sm:w-auto"
                  onClick={() => void handleAction(item.id)}
                >
                  {item.actionLabel}
                </Button>
                {item.actions?.length ? (
                  <div className="flex flex-wrap gap-2 sm:justify-end">
                    {item.actions.map((action) => {
                      const actionKey = `${item.id}:${action.id}`;
                      const isBusy = busyAction === actionKey;
                      const isDone = completedAction === actionKey;
                      return (
                        <Button
                          key={action.id}
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="h-8 px-3 text-xs"
                          onClick={() => void handleAction(item.id, action.id)}
                          disabled={isBusy}
                        >
                          {isBusy ? "Working…" : isDone ? "Saved" : action.label}
                        </Button>
                      );
                    })}
                  </div>
                ) : null}
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { UserUnderstanding } from "../../types/user-understanding";

type LearnedInsightsProps = {
  items: UserUnderstanding[];
  learningEnabled: boolean;
  onLearningChange: (enabled: boolean) => Promise<void>;
  onEdit: (item: UserUnderstanding, value: string) => Promise<void>;
  onDelete: (item: UserUnderstanding) => Promise<void>;
};

export function LearnedInsights({ items, learningEnabled, onLearningChange, onEdit, onDelete }: LearnedInsightsProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");

  return (
    <section className="rounded-xl border border-border bg-white px-5 py-5 sm:px-6">
      <div className="flex flex-col gap-4 border-b border-border pb-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-stone-950">What Synzept Has Learned</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-stone-500">
            Approved patterns from the Learning Engine. Nothing appears here until you accept it.
          </p>
        </div>
        <label className="flex shrink-0 items-center gap-2 text-xs font-medium text-stone-600">
          <input type="checkbox" checked={learningEnabled} onChange={(event) => void onLearningChange(event.target.checked)} className="h-4 w-4 accent-stone-800" />
          Allow future learning
        </label>
      </div>

      <div className="divide-y divide-border">
        {items.length === 0 && <p className="py-5 text-sm text-stone-400">No learned insights. You are fully in control.</p>}
        {items.map((item) => (
          <div key={item.id} className="py-4">
            {editingId === item.id ? (
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input value={draft} onChange={(event) => setDraft(event.target.value)} />
                <Button size="sm" onClick={async () => { await onEdit(item, draft); setEditingId(null); }}>Save</Button>
              </div>
            ) : (
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm font-medium text-stone-900">{item.value}</p>
                  <p className="mt-1 text-xs text-muted">
                    Source: Learned by Synzept
                    {item.confidence !== null ? ` · Confidence: ${Math.round(item.confidence * 100)}%` : ""}
                    {item.learned_at ? ` · Learned ${new Date(item.learned_at).toLocaleDateString()}` : ""}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="ghost" onClick={() => { setEditingId(item.id); setDraft(item.value); }}>Edit</Button>
                  <Button size="sm" variant="ghost" onClick={() => void onDelete(item)}>Delete</Button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, Loader2, ThumbsUp } from "lucide-react";
import { PageFrame } from "@frontend/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type FeatureRequest } from "@/lib/api";

const statusLabels: Record<string, string> = {
  planned: "Planned",
  in_progress: "In Progress",
  shipped: "Shipped",
  new: "Requested",
};

export default function FeedbackPage() {
  const [items, setItems] = useState<FeatureRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [voting, setVoting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .listFeatureRequests()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Feature requests could not load."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const grouped = useMemo(() => {
    const groups: Record<string, FeatureRequest[]> = { planned: [], in_progress: [], shipped: [], new: [] };
    for (const item of items) {
      const key = item.status in groups ? item.status : "new";
      groups[key].push(item);
    }
    for (const key of Object.keys(groups)) {
      groups[key].sort((a, b) => b.demand_score - a.demand_score || b.votes - a.votes);
    }
    return groups;
  }, [items]);

  const vote = async (item: FeatureRequest) => {
    if (item.user_voted || voting) return;
    setVoting(item.id);
    try {
      const result = await api.voteFeatureRequest(item.id);
      setItems((current) => current.map((row) => (row.id === item.id ? { ...row, votes: result.votes, user_voted: true } : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Vote could not be saved.");
    } finally {
      setVoting(null);
    }
  };

  return (
    <PageFrame eyebrow="Product feedback" title="Feature Requests">
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <p className="text-sm font-semibold text-stone-950">Vote on what Synzept should build next.</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">Submitted feature requests are grouped by roadmap status. Your votes help shape priority.</p>
        </section>
        {loading ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-72 rounded-lg" />)}
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-3">
            {(["planned", "in_progress", "shipped"] as const).map((status) => (
              <FeatureColumn key={status} title={statusLabels[status]} items={grouped[status]} onVote={vote} voting={voting} />
            ))}
          </div>
        )}
        {!loading && grouped.new.length > 0 && (
          <FeatureColumn title="Requested" items={grouped.new} onVote={vote} voting={voting} wide />
        )}
      </div>
    </PageFrame>
  );
}

function FeatureColumn({
  title,
  items,
  onVote,
  voting,
  wide = false,
}: {
  title: string;
  items: FeatureRequest[];
  onVote: (item: FeatureRequest) => void;
  voting: string | null;
  wide?: boolean;
}) {
  return (
    <section className={`rounded-lg border border-border bg-white p-4 shadow-soft ${wide ? "lg:p-5" : ""}`}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-stone-950">{title}</p>
        <span className="rounded-md bg-stone-100 px-2 py-1 text-xs text-muted">{items.length}</span>
      </div>
      <div className={`mt-3 grid gap-3 ${wide ? "md:grid-cols-2 lg:grid-cols-3" : ""}`}>
        {items.map((item) => (
          <article key={item.id} className="rounded-md bg-stone-50 p-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="line-clamp-2 text-sm font-medium text-stone-950">{item.title}</p>
                <p className="mt-1 line-clamp-3 text-xs leading-5 text-muted-foreground">{item.detail}</p>
              </div>
              {item.status === "shipped" ? <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" /> : null}
            </div>
            <div className="mt-3 flex items-center justify-between gap-2">
              <span className="rounded-md bg-white px-2 py-1 text-[11px] text-stone-600">{item.category}</span>
              <Button size="sm" variant={item.user_voted ? "ghost" : "outline"} onClick={() => onVote(item)} disabled={item.user_voted || voting === item.id}>
                {voting === item.id ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <ThumbsUp className="mr-1.5 h-3.5 w-3.5" />}
                {item.votes}
              </Button>
            </div>
          </article>
        ))}
        {!items.length && <p className="rounded-md bg-stone-50 px-3 py-4 text-sm leading-6 text-muted-foreground">Nothing here yet.</p>}
      </div>
    </section>
  );
}

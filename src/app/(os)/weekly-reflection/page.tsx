"use client";

import { useCallback, useEffect, useState, useTransition } from "react";
import type { ComponentType } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, History, RefreshCw, Target, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type IntelligenceItem, type WeeklyReview } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

export default function WeeklyReflectionPage() {
  const [review, setReview] = useState<WeeklyReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, startRefresh] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .generateWeeklyReview()
      .then(setReview)
      .catch(() => setError("Weekly reflection could not load. Your workspace is still safe."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const refresh = () => {
    startRefresh(() => {
      void load();
    });
  };

  return (
    <PageFrame
      eyebrow="Reflection"
      title="Weekly Review"
      action={
        <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing || loading}>
          <RefreshCw className={`mr-1.5 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      }
    >
      <div className="mx-auto max-w-5xl space-y-4 p-4 pb-24 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {loading ? (
          <WeeklySkeleton />
        ) : (
          <div className="space-y-4">
            <section className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft">
              <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
                <History className="h-3.5 w-3.5" />
                {review ? `${formatDate(review.period_start)} to ${formatDate(review.period_end)}` : "This week"}
              </p>
              <h2 className="mt-3 text-2xl font-semibold leading-8">What changed, what slipped, and what to do next.</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-300">
                Synzept reviews wins, missed goals, progress patterns, and the next moves that keep continuity alive.
              </p>
            </section>

            <div className="grid gap-4 lg:grid-cols-2">
              <ReviewList title="Wins" icon={CheckCircle2} items={review?.wins || []} fallback="No completed wins were recorded this week yet." />
              <ReviewList title="Missed Goals" icon={TriangleAlert} items={review?.missed_objectives || []} fallback="No missed goals were detected." />
              <ReviewList title="Progress" icon={Target} items={review?.progress_made || []} fallback="Project movement will appear here as work changes." />
              <RecommendationList items={review?.suggested_next_steps || []} />
            </div>
          </div>
        )}
      </div>
    </PageFrame>
  );
}

function ReviewList({ title, icon: Icon, items, fallback }: { title: string; icon: ComponentType<{ className?: string }>; items: string[]; fallback: string }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
        <Icon className="h-4 w-4 text-muted" />
        {title}
      </p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 8).map((item) => (
          <p key={item} className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-stone-800">{item}</p>
        ))}
        {!items.length && <p className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-muted-foreground">{fallback}</p>}
      </div>
    </section>
  );
}

function RecommendationList({ items }: { items: IntelligenceItem[] }) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
        <ArrowRight className="h-4 w-4 text-muted" />
        Recommendations
      </p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 6).map((item) => (
          <Link key={`${item.type}-${item.title}`} href={item.project_id ? `/projects/${item.project_id}` : "/dashboard"} className="block rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
            <p className="text-sm font-medium text-stone-950">{item.title}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </Link>
        ))}
        {!items.length && <p className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-muted-foreground">Create or update work this week and Synzept will recommend next moves.</p>}
      </div>
    </section>
  );
}

function WeeklySkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-44 rounded-lg" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-64 rounded-lg" />
        <Skeleton className="h-64 rounded-lg" />
      </div>
    </div>
  );
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

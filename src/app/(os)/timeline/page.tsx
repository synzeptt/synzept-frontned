"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CalendarDays, CheckCircle2, Clock3 } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { ProGate } from "@/components/pro/pro-gate";
import { api, type Dashboard, type TimelineEvent } from "@/lib/api";
import { sampleTimelineItems } from "@/lib/sample-data";
import { PageFrame } from "@frontend/components/layout/page-frame";

type TimelineItem = {
  id: string;
  title: string;
  detail: string;
  date: string;
  href?: string;
  type: string;
};

export default function TimelinePage() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([
      api.getDashboard(),
      api.listTimelineEvents().catch(() => []),
    ])
      .then(([dashboardData, eventRows]) => {
        setDashboard(dashboardData);
        setEvents(eventRows);
      })
      .catch(() => setError("Timeline could not load. Your workspace is still safe."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const realItems = useMemo(() => getTimelineItems(dashboard, events), [dashboard, events]);
  const items = realItems.length ? realItems : sampleTimelineItems;
  const grouped = useMemo(() => {
    const byDate = new Map<string, TimelineItem[]>();
    for (const item of items) {
      const key = formatDateKey(item.date);
      byDate.set(key, [...(byDate.get(key) || []), item]);
    }
    return [...byDate.entries()].sort(([a], [b]) => b.localeCompare(a));
  }, [items]);

  return (
    <PageFrame eyebrow="Timeline" title="What Changed">
      <ProGate feature="Timeline Intelligence" description="Timeline Intelligence is a Synzept Pro feature that tracks project movement, milestones, decisions, and important events.">
      <div className="mx-auto max-w-5xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
            <Clock3 className="h-4 w-4 text-muted" />
            Return history
          </p>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            A simple record of project movement, completed work, decisions, and meaningful progress.
          </p>
        </section>

        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-28 rounded-lg" />
            <Skeleton className="h-28 rounded-lg" />
          </div>
        ) : (
          <div className="space-y-5">
            {grouped.map(([date, rows]) => (
              <section key={date} className="rounded-lg border border-border bg-white p-5 shadow-soft">
                <p className="mb-4 flex items-center gap-2 text-sm font-medium text-stone-950">
                  <CalendarDays className="h-4 w-4 text-muted" />
                  {formatDisplayDate(date)}
                </p>
                <div className="space-y-2">
                  {rows.map((item) => (
                    <TimelineRow key={item.id} item={item} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
      </ProGate>
    </PageFrame>
  );
}

function TimelineRow({ item }: { item: TimelineItem }) {
  const content = (
    <div className="flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
      <div className="flex min-w-0 gap-3">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
        <div className="min-w-0">
          <p className="line-clamp-1 text-sm font-medium text-stone-900">{item.title}</p>
          <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail || item.type}</p>
        </div>
      </div>
      {item.href && <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 text-stone-400" />}
    </div>
  );

  return item.href ? <Link href={item.href}>{content}</Link> : content;
}

function getTimelineItems(dashboard: Dashboard | null, events: TimelineEvent[]): TimelineItem[] {
  const activity = (dashboard?.recent_activity || []).map((item) => ({
    id: `activity-${item.id}`,
    title: item.title,
    detail: item.description || item.type,
    date: item.occurred_at,
    href: item.project_id ? `/projects/${item.project_id}` : undefined,
    type: item.type,
  }));
  const projectChanges = (dashboard?.projects || []).slice(0, 8).map((project) => ({
    id: `project-${project.id}`,
    title: project.name,
    detail: project.currentFocus || project.recommendedNextStep || project.description || "Project updated",
    date: project.updatedAt || project.createdAt || project.created_at,
    href: `/projects/${project.id}`,
    type: "project",
  }));
  const timelineEvents = events.map((event) => ({
    id: `event-${event.id}`,
    title: event.title,
    detail: event.description || event.eventType,
    date: event.eventDate || event.createdAt,
    href: event.projectId ? `/projects/${event.projectId}` : undefined,
    type: event.eventType,
  }));

  return [...activity, ...timelineEvents, ...projectChanges]
    .filter((item) => item.date)
    .sort((a, b) => String(b.date).localeCompare(String(a.date)))
    .slice(0, 30);
}

function formatDateKey(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value.slice(0, 10);
  return date.toISOString().slice(0, 10);
}

function formatDisplayDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" });
}

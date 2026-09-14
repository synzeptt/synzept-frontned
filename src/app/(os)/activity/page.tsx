"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";
import { api, type WorkspaceActivity } from "@/lib/api";
import { Page } from "@/components/design-system/workspace-primitives";

function formatDate(date: Date): string {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);

  const input = new Date(date);
  input.setHours(0, 0, 0, 0);

  if (input.getTime() === today.getTime()) {
    return "Today";
  }
  if (input.getTime() === yesterday.getTime()) {
    return "Yesterday";
  }

  return input.toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

export default function ActivityPage() {
  const [activities, setActivities] = useState<WorkspaceActivity[]>([]);
  const [loading, setLoading] = useState(true);

  const loadActivities = useCallback(async () => {
    try {
      const rows = await api.getWorkspaceTimeline(100);
      setActivities(rows);
    } catch {
      setActivities([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadActivities();
  }, [loadActivities]);

  const grouped = useMemo(() => {
    const groups: Record<string, WorkspaceActivity[]> = {};

    activities.forEach((activity) => {
      const dateGroup = formatDate(new Date(activity.created_at));
      if (!groups[dateGroup]) {
        groups[dateGroup] = [];
      }
      groups[dateGroup].push(activity);
    });

    return groups;
  }, [activities]);

  const dateGroups = useMemo(
    () =>
      Object.entries(grouped).sort((a, b) => {
        const dateA = new Date(a[1][0]?.created_at || 0);
        const dateB = new Date(b[1][0]?.created_at || 0);
        return dateB.getTime() - dateA.getTime();
      }),
    [grouped]
  );

  return (
    <Page>
      <div className="mx-auto max-w-3xl px-5 py-12 sm:px-8 sm:py-16">
        <div className="mb-10">
          <p className="synzept-eyebrow mb-3">Review</p>
          <h1 className="text-[1.875rem] font-semibold leading-tight tracking-[-0.035em] text-stone-950">Your week</h1>
          <p className="mt-2 text-[15px] leading-6 text-stone-600">A quiet record of what moved through your workspace.</p>
        </div>

        {/* Timeline */}
        <div className="mt-8 space-y-8">
          {loading ? (
            <div className="text-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-stone-400 mx-auto mb-4" />
              <p className="text-stone-600">Loading activity...</p>
            </div>
          ) : dateGroups.length === 0 ? (
            <div className="border-y border-dashed border-stone-300 py-12 text-center">
              <p className="text-stone-600">No activity yet</p>
              <p className="text-sm text-stone-500 mt-1">
                Your workspace activity will appear here
              </p>
            </div>
          ) : (
            dateGroups.map(([dateLabel, items]) => (
              <div key={dateLabel}>
                <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-500 mb-4">
                  {dateLabel}
                </h2>
                <div className="divide-y divide-border/[0.08]">
                  {items.map((activity) => (
                    <div
                      key={activity.id}
                      className="flex gap-4 border-t border-transparent py-4 transition-colors hover:bg-surface-overlay/50"
                    >
                      <div className="text-sm font-mono text-stone-500 flex-shrink-0">
                        {formatTime(activity.created_at)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-stone-900">
                          {activity.title || activity.action}
                        </p>
                        {activity.detail && (
                          <p className="text-xs text-stone-600 mt-1 line-clamp-2">
                            {activity.detail}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Page>
  );
}

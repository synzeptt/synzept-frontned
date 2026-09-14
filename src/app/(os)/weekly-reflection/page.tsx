"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import Link from "next/link";
import { ArrowRight, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { WorkspacePage } from "@/components/layout/workspace-content";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type CalendarWeeklyContext, type DailyBriefSnapshot, type IntelligenceItem, type MemoryTrustRecord, type WeeklyReview } from "@/lib/api";
import { buildWeeklyExecutiveReviewSnapshot } from "@/lib/flagship-experiences";
import { useConnectedAppsStore } from "@/stores/connected-apps";

export default function WeeklyReflectionPage() {
  const [review, setReview] = useState<WeeklyReview | null>(null);
  const [understanding, setUnderstanding] = useState<MemoryTrustRecord[]>([]);
  const [calendar, setCalendar] = useState<CalendarWeeklyContext | null>(null);
  const [dailyBrief, setDailyBrief] = useState<DailyBriefSnapshot | null>(null);
  const { apps: connectedApps, refresh: refreshConnectedApps } = useConnectedAppsStore();
  const [loading, setLoading] = useState(true);
  const [refreshing, startRefresh] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((background = false) => {
    if (!background) setLoading(true);
    setError(null);
    return Promise.all([
      api.generateWeeklyReview(),
      api.relevantUnderstanding(undefined, undefined, 12).catch(() => []),
      api.getGoogleCalendarWeeklyContext().catch(() => null),
      api.getMicrosoftCalendarWeeklyContext().catch(() => null),
      api.getDailyBriefV2().catch(() => null),
      refreshConnectedApps(background).catch(() => ({})),
    ])
      .then(([nextReview, understandingRows, googleCalendarContext, microsoftCalendarContext, daily]) => {
        setReview(nextReview);
        setUnderstanding(understandingRows as MemoryTrustRecord[]);
        setCalendar(mergeWeeklyCalendars(googleCalendarContext, microsoftCalendarContext));
        setDailyBrief(daily);
      })
      .catch(() => setError("Weekly reflection could not load. Your workspace is still safe."))
      .finally(() => {
        if (!background) setLoading(false);
      });
  }, [refreshConnectedApps]);

  useEffect(() => {
    void load();
    const refreshContext = () => {
      void load(true);
    };
    window.addEventListener("synzept:context-cache-cleared", refreshContext);
    return () => window.removeEventListener("synzept:context-cache-cleared", refreshContext);
  }, [load]);

  const refresh = () => {
    startRefresh(() => {
      void load();
    });
  };

  const calendarConnected = Boolean(connectedApps.google_calendar?.connected);
  const reflection = useMemo(() => buildUnderstandingReflection(review, understanding, calendar, dailyBrief), [calendar, dailyBrief, review, understanding]);
  const flagshipReview = useMemo(() => buildWeeklyExecutiveReviewSnapshot({
    headline: reflection.headline,
    summary: reflection.summary,
    wins: reflection.improved.slice(0, 3),
    challenges: reflection.slowedDown.slice(0, 3),
    progressByProject: reflection.changed.slice(0, 2).map((item) => ({ project: "Focus area", detail: item })),
    risks: reflection.causes.slice(0, 3),
    missedCommitments: reflection.slowedDown.slice(0, 2),
    lessonsLearned: reflection.patterns.slice(0, 2),
    suggestedPriorities: [reflection.nextWeekRecommendation],
    strategicRecommendations: [reflection.recommendationWhy],
  }), [reflection.causes, reflection.changed, reflection.headline, reflection.improved, reflection.nextWeekRecommendation, reflection.patterns, reflection.recommendationWhy, reflection.slowedDown, reflection.summary]);

  useEffect(() => {
    if (!reflection.nextAnchor) return;
    try {
      localStorage.setItem(
        "synzept_weekly_handoff",
        JSON.stringify({
          anchor: reflection.nextAnchor,
          recommendation: reflection.nextWeekRecommendation,
          createdAt: new Date().toISOString(),
        }),
      );
    } catch {
      /* The review still works if storage is unavailable. */
    }
  }, [reflection.nextAnchor, reflection.nextWeekRecommendation]);

  return (
    <div className="min-h-full bg-[#faf9f6]">
      <WorkspacePage as="div" className="max-w-[920px] space-y-12 pb-24 pt-12 sm:pt-16">
        <RecoveryBanner message={error} onRetry={load} />
        {loading ? (
          <WeeklySkeleton />
        ) : (
          <article className="motion-safe:animate-fade-in">
            <header>
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Weekly coaching</p>
                  <p className="mt-2 text-sm text-stone-400">{review ? `${formatDate(review.period_start)} to ${formatDate(review.period_end)}` : "This week"}</p>
                </div>
                <Button size="sm" variant="ghost" onClick={refresh} disabled={refreshing || loading}>
                  <RefreshCw className={`mr-1.5 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
              </div>
              <h1 className="mt-8 max-w-3xl text-4xl font-medium leading-[1.08] tracking-[-0.045em] text-[#18212f] sm:text-6xl">{reflection.headline}</h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-stone-600">
                {reflection.summary}
              </p>
              {reflection.nextAnchor ? <p className="mt-6 text-sm font-medium text-stone-800">Tomorrow starts from {reflection.nextAnchor}.</p> : null}
            </header>

            <section className="mt-12 border-y border-stone-200/80 py-8">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-400">Weekly Executive Review</p>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.02em] text-stone-950">{flagshipReview.headline}</h2>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-stone-600">{flagshipReview.summary}</p>
              <div className="mt-8 grid gap-8 border-t border-stone-200/80 pt-6 md:grid-cols-2">
                <ReviewList title="Suggested priorities" items={flagshipReview.suggestedPriorities} fallback="No priority has emerged yet." />
                <ReviewList title="Strategic recommendations" items={flagshipReview.strategicRecommendations} fallback="No recommendation has emerged yet." />
              </div>
            </section>

            <div className="mt-16 border-t border-stone-200/80 pt-10">
              <RecommendationList items={review?.suggested_next_steps || []} anchor={reflection.nextAnchor} coaching={reflection.nextWeekRecommendation} why={reflection.recommendationWhy} />
            </div>

            <div className="mt-16 divide-y divide-stone-200/80 border-y border-stone-200/80">
              <div className="grid gap-0 sm:grid-cols-2 sm:gap-12">
                <ReviewList title="What changed" items={reflection.changed} fallback="Keep using Today and Think. Movement will appear here." />
                <ReviewList title="Why it happened" items={reflection.causes} fallback="There is not enough evidence to name the cause yet." />
              </div>
              <details className="group py-6">
                <summary className="cursor-pointer list-none text-sm font-medium text-stone-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/20">More from this week</summary>
                <div className="mt-4 grid gap-0 sm:grid-cols-3 sm:gap-8">
                <ReviewList title="What went well" items={reflection.improved} fallback="Complete one task or close one loop." />
                <ReviewList title="Patterns" items={reflection.patterns} fallback="Approve one useful understanding update." />
                <ReviewList title="Calendar" items={reflection.calendarSignals} fallback={calendarConnected ? "Your calendar is clear today. This is a good opportunity for focused work." : "Connect Google Calendar."} />
                </div>
              </details>
              <div>
                <TodaysThreadReviewCard dailyBrief={dailyBrief} />
              </div>
            </div>
          </article>
        )}
      </WorkspacePage>
    </div>
  );
}

function TodaysThreadReviewCard({ dailyBrief }: { dailyBrief: DailyBriefSnapshot | null }) {
  const thread = dailyBrief?.todaysThread;
  const primary = itemText(thread?.primaryRecommendation, "title");
  if (!primary) return null;
  return (
    <section className="py-6">
      <p className="text-sm font-semibold text-stone-950">Today&apos;s Thread carried forward</p>
      <p className="mt-2 text-sm font-medium leading-6 text-stone-900">{primary}</p>
      <p className="mt-2 text-sm leading-6 text-stone-600">{thread?.whyItMattersToday}</p>
      {thread?.risksIfIgnored?.length ? <p className="mt-2 text-xs leading-5 text-stone-500">If ignored: {thread.risksIfIgnored[0]}</p> : null}
    </section>
  );
}

function ReviewList({ title, items, fallback }: { title: string; items: string[]; fallback: string }) {
  return (
    <section className="py-6">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-stone-400">{title}</p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 4).map((item) => (
          <p key={item} className="text-sm leading-6 text-stone-700">{item}</p>
        ))}
        {!items.length && <p className="text-sm leading-6 text-stone-500">{fallback}</p>}
      </div>
    </section>
  );
}

function RecommendationList({ items, anchor, coaching, why }: { items: IntelligenceItem[]; anchor: string | null; coaching: string; why: string }) {
  return (
    <section>
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-stone-400">
        <ArrowRight className="h-4 w-4 text-accent" />
        What should happen next week
      </p>
      {anchor ? <p className="mt-5 text-xl font-medium leading-8 tracking-[-0.02em] text-stone-900">Anchor next week around {anchor}.</p> : null}
      <p className="mt-3 max-w-3xl text-lg leading-8 text-stone-700">{coaching}</p>
      <p className="mt-5 max-w-2xl text-sm leading-6 text-stone-500">
        <span className="font-medium text-stone-900">Why: </span>
        {why}
      </p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 3).map((item) => (
          <Link key={`${item.type}-${item.title}`} href={item.project_id ? `/projects/${item.project_id}` : "/home"} className="block border-t border-stone-200/70 py-3 transition hover:text-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/20">
            <p className="text-sm font-medium text-stone-950">{item.title}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </Link>
        ))}
        {!items.length && <p className="text-sm leading-6 text-muted-foreground">Create or update one piece of work.</p>}
      </div>
    </section>
  );
}

function buildUnderstandingReflection(review: WeeklyReview | null, understanding: MemoryTrustRecord[], calendar: CalendarWeeklyContext | null, dailyBrief: DailyBriefSnapshot | null) {
  const active = understanding.filter((item) => !item.archived_at);
  const focus = byCategory(active, ["current_focus", "priorities"]);
  const goal = byCategory(active, ["goals"]);
  const project = byCategory(active, ["projects"]);
  const habit = byCategory(active, ["habits", "work_patterns"]);
  const preference = byCategory(active, ["preferences", "communication_style", "learning_style", "decision_style"]);
  const anchor = focus || goal || project;
  const todaysThread = itemText(dailyBrief?.todaysThread?.primaryRecommendation, "title");
  const changed = [
    focus ? `Your current focus is now: ${focus}` : null,
    project ? `The clearest active project signal is: ${project}` : null,
    ...(review?.progress_made || []).slice(0, 3),
  ].filter((item): item is string => Boolean(item));
  const improved = [
    ...(review?.wins || []).slice(0, 4),
    habit ? `Synzept noticed this useful pattern: ${habit}` : null,
    preference ? `Synzept can respond better because it understands this preference: ${preference}` : null,
  ].filter((item): item is string => Boolean(item));
  const lessImportant = active
    .filter((item) => normalizeCategory(item.category || item.memory_type) === "current_focus" && item.content !== focus)
    .slice(0, 3)
    .map((item) => `${item.content} appears less central than ${focus || anchor || "your current work"}.`);
  const slowedDown = [
    ...(review?.missed_objectives || []).slice(0, 3),
    calendar && calendar.meetingLoadMinutes >= 900 ? `Calendar shows ${Math.round(calendar.meetingLoadMinutes / 60)} hours in scheduled events this week.` : null,
    active.find((item) => normalizeCategory(item.category || item.memory_type) === "current_blockers")?.content || null,
  ].filter((item): item is string => Boolean(item));
  const patterns = [
    habit ? `Work pattern: ${habit}` : null,
    preference ? `Response preference: ${preference}` : null,
    calendar && calendar.recurringEvents >= 3 ? `${calendar.recurringEvents} recurring calendar events shaped the week.` : null,
    focus && project ? `Most visible work this week connects ${focus} to ${project}.` : null,
  ].filter((item): item is string => Boolean(item));
  const calendarSignals = calendar
    ? [
        calendar.meetingLoadMinutes >= 900 ? "Scheduled commitments crowded out protected focus time." : "Your schedule left useful room for deliberate work.",
        calendar.heavyMeetingDays.length ? `Meeting pressure was concentrated on ${calendar.heavyMeetingDays.join(", ")}.` : null,
        calendar.recurringEvents ? "Recurring commitments repeatedly shaped the time available for focused work." : null,
      ].filter((item): item is string => Boolean(item))
    : [];
  const nextWeekRecommendation = todaysThread
      ? `Carry forward Today's Thread first: ${todaysThread}. Keep it small and evidence-backed.`
      : anchor
      ? `Next week, keep the plan smaller than the ambition: choose one visible outcome for ${anchor}, then clear or consciously defer unfinished loops before adding new work.`
      : "Next week, start by approving one current focus or goal so Synzept can coach from evidence instead of guessing.";
  const recommendationWhy = calendar && calendar.meetingLoadMinutes >= 900
    ? `I am recommending a smaller week because Calendar shows about ${Math.round(calendar.meetingLoadMinutes / 60)} hours in scheduled events, and ${todaysThread || anchor || "your current work"} needs protected space.`
    : todaysThread
      ? `I am recommending this because Today's Thread already connects the strongest daily evidence to ${todaysThread}.`
    : anchor
      ? `I am recommending this because approved understanding points to ${anchor}, and this week's review should carry one clear thread forward.`
      : "I am not confident enough to personalize this strongly yet because there is no approved current focus, goal, or project anchor.";

  const causes = [
    calendar && calendar.meetingLoadMinutes >= 900 ? "Scheduled commitments fragmented the time available for focused work." : null,
    slowedDown[0] ? `The clearest friction was: ${slowedDown[0]}` : null,
    habit ? `Your established work pattern also mattered: ${habit}` : null,
  ].filter((item): item is string => Boolean(item));

  const progressCount = review?.wins?.length || 0;
  const frictionCount = review?.missed_objectives?.length || 0;
  const headline = calendar && calendar.meetingLoadMinutes >= 900
    ? "Your week became more fragmented than your priorities allowed."
    : frictionCount > progressCount
      ? "Friction displaced more strategic progress than it should have."
      : anchor
        ? `You moved ${anchor} forward without losing the larger thread.`
        : "The week needs a clearer strategic anchor.";
  const summary = calendar && calendar.meetingLoadMinutes >= 900
    ? `The issue was not effort. Scheduled commitments repeatedly competed with ${todaysThread || anchor || "the work that mattered most"}.`
    : frictionCount > progressCount
      ? `The week produced useful movement, but unresolved work accumulated faster than it closed.`
      : anchor
        ? `The strongest evidence points to continued movement around ${anchor}. Next week should protect that direction rather than widen it.`
        : "Approve one current focus, goal, or project so next week can begin from judgment instead of guesswork.";

  return {
    headline,
    summary,
    changed: changed.length ? changed : review?.progress_made || [],
    improved,
    lessImportant,
    slowedDown,
    causes,
    patterns,
    calendarSignals,
    nextWeekRecommendation,
    recommendationWhy,
    nextAnchor: anchor,
  };
}

function mergeWeeklyCalendars(google: CalendarWeeklyContext | null, microsoft: CalendarWeeklyContext | null): CalendarWeeklyContext | null {
  if (!google) return microsoft;
  if (!microsoft) return google;
  return {
    events: google.events + microsoft.events,
    meetingLoadMinutes: google.meetingLoadMinutes + microsoft.meetingLoadMinutes,
    recurringEvents: google.recurringEvents + microsoft.recurringEvents,
    heavyMeetingDays: [...new Set([...google.heavyMeetingDays, ...microsoft.heavyMeetingDays])],
    summary: `${google.summary} ${microsoft.summary}`.trim(),
  };
}

function itemText(item: Record<string, unknown> | null | undefined, key: string) {
  const value = item?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function byCategory(items: MemoryTrustRecord[], categories: string[]) {
  return items.find((item) => categories.includes(normalizeCategory(item.category || item.memory_type)))?.content || null;
}

function normalizeCategory(value?: string | null) {
  return (value || "other").toLowerCase().replace(/[-\s]+/g, "_");
}

function WeeklySkeleton() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-500">Reviewing Today&apos;s Thread and recent progress...</p>
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

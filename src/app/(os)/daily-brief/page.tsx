"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, CalendarDays, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type DailyBriefSnapshot } from "@/lib/api";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";

type BriefItem = {
  type?: string;
  title: string;
  detail?: string;
  href?: string | null;
  priority?: string;
  source?: string;
};

type DailyContent = {
  briefDate: string;
  currentMission: Record<string, unknown>;
  currentFocus: Record<string, unknown>;
  whatChanged: Array<Record<string, unknown>>;
  whatMattersToday: Array<Record<string, unknown>>;
  openLoops: Array<Record<string, unknown>>;
  recommendedNextStep: Record<string, unknown>;
  focusForToday: Record<string, unknown>;
  recentDecisions: Array<Record<string, unknown>>;
  upcomingPriorities: Array<Record<string, unknown>>;
  updatedAt?: string | null;
  createdAt?: string | null;
};

export default function DailyBriefPage() {
  const router = useRouter();
  const [brief, setBrief] = useState<DailyBriefSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, startRefresh] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((refresh = false) => {
    setLoading(!refresh);
    setError(null);
    const request = refresh ? api.refreshDailyBriefV2() : api.getDailyBriefV2();
    return request
      .then(setBrief)
      .catch(() => setError("Daily Brief could not load. Your workspace is still safe."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    void api.trackEvent("daily_brief_viewed", "daily_brief");
  }, []);

  const daily = useMemo(() => toDailyContent(brief), [brief]);
  const mission = useMemo(() => toItem(daily.currentMission, "Build one clear continuity anchor for today's work."), [daily]);
  const focus = useMemo(() => toItem(daily.currentFocus, "Choose one meaningful priority for today."), [daily]);
  const nextAction = useMemo(() => toItem(daily.recommendedNextStep, "Continue today's most important work."), [daily]);
  const focusForToday = useMemo(() => toItem(daily.focusForToday, focus.title), [daily, focus.title]);

  const refresh = () => {
    startRefresh(() => {
      void load(true);
    });
  };

  const continueToday = () => {
    const prompt = [
      "Continue today's work from my Daily Brief.",
      "",
      `Current Mission: ${mission.title}`,
      `Current Focus: ${focus.title}`,
      `Focus For Today: ${focusForToday.title}`,
      `Recommended Next Action: ${nextAction.title}`,
      `Open Loops: ${toItems(daily.openLoops).map((item) => item.title).join("; ") || "None visible"}`,
      "",
      "Do not ask me to re-explain. Help me continue from this brief.",
    ].join("\n");
    localStorage.setItem(CHAT_DRAFT_KEY, prompt);
    void api.trackEvent("daily_continue_today_clicked", "daily_brief", {
      recommended_next_action: nextAction.title,
      open_loops: daily.openLoops.length,
    });
    router.push("/chat");
  };

  return (
    <PageFrame
      eyebrow="Daily"
      title="Brief"
      action={
        <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing || loading}>
          <RefreshCw className={`mr-1.5 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      }
    >
      <div className="min-h-full bg-white text-stone-950">
        <div className="mx-auto max-w-5xl space-y-5 px-4 py-6 pb-24 sm:px-6 lg:px-8 lg:py-10">
          <RecoveryBanner message={error} onRetry={() => load()} />
          {loading ? (
            <DailySkeleton />
          ) : (
            <>
              <header className="space-y-5">
                <div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-stone-400">
                  <CalendarDays className="h-3.5 w-3.5" />
                  <span>{formatBriefDate(daily.briefDate)}</span>
                  <span>/</span>
                  <span>Good Morning</span>
                </div>
                <div className="grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
                  <div>
                    <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-normal sm:text-5xl">
                      Good Morning
                    </h1>
                    <p className="mt-4 max-w-3xl text-lg leading-8 text-stone-600">{mission.title}</p>
                  </div>
                  <Button onClick={continueToday} className="h-12 px-5">
                    Continue Today&apos;s Work
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </div>
              </header>

              <section className="rounded-lg border border-stone-200 bg-[#fbfbf8] p-5 shadow-[0_14px_42px_rgba(32,31,28,0.07)] sm:p-6">
                <p className="flex items-center gap-2 text-sm font-medium text-stone-500">
                  <Sparkles className="h-4 w-4" />
                  Recommended Next Action
                </p>
                <h2 className="mt-3 text-3xl font-semibold leading-tight text-stone-950">{nextAction.title}</h2>
                <p className="mt-3 max-w-3xl text-base leading-7 text-stone-600">
                  {nextAction.detail || "This is the clearest continuation point in your workspace."}
                </p>
              </section>

              <div className="grid gap-4 lg:grid-cols-2">
                <DailySection index={1} title="What Changed" items={toItems(daily.whatChanged)} empty="No meaningful changes since the last brief yet." />
                <DailySection index={2} title="What Matters Today" items={toItems(daily.whatMattersToday)} empty="Add projects, tasks, or notes and Synzept will identify today's priorities." />
                <DailySection index={3} title="Open Loops Requiring Attention" items={toItems(daily.openLoops)} empty="No open loops need attention right now." />
                <DailySection index={4} title="Recommended Next Action" items={[nextAction]} empty="Choose one meaningful priority for today." />
                <DailySection index={5} title="Focus For Today" items={[focusForToday]} empty="Set one focus to make today easier to resume." />
                <DailySection title="Upcoming Priorities" items={toItems(daily.upcomingPriorities)} empty="No upcoming priority is pulling focus yet." />
              </div>

              <footer className="rounded-lg border border-stone-200 bg-white p-4 text-sm leading-6 text-stone-500">
                Daily Brief is generated from your current mission, current focus, open loops, recent progress, recent decisions, and upcoming priorities.
                {daily.updatedAt || daily.createdAt ? ` Last refreshed ${formatTime(daily.updatedAt || daily.createdAt || "")}.` : ""}
              </footer>
            </>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

function DailySection({ index, title, items, empty }: { index?: number; title: string; items: BriefItem[]; empty: string }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-[0_10px_30px_rgba(32,31,28,0.05)] sm:p-5">
      <div className="flex items-center gap-3">
        {index ? (
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-950 text-xs font-semibold text-white">
            {index}
          </span>
        ) : null}
        <h2 className="text-base font-semibold text-stone-950">{title}</h2>
      </div>
      <div className="mt-4 space-y-2">
        {items.filter((item) => item.title).slice(0, 5).map((item) => (
          <BriefRow key={`${title}-${item.title}`} item={item} />
        ))}
        {!items.filter((item) => item.title).length ? (
          <p className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-stone-500">{empty}</p>
        ) : null}
      </div>
    </section>
  );
}

function BriefRow({ item }: { item: BriefItem }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="line-clamp-2 text-sm font-medium leading-5 text-stone-950">{item.title}</p>
          {item.detail ? <p className="mt-1 line-clamp-2 text-sm leading-6 text-stone-600">{item.detail}</p> : null}
        </div>
        {item.priority && item.priority !== "medium" ? (
          <span className="shrink-0 rounded-md bg-white px-2 py-1 text-[11px] capitalize text-stone-600">{item.priority}</span>
        ) : null}
      </div>
    </div>
  );
}

function DailySkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-36 rounded-lg" />
      <Skeleton className="h-48 rounded-lg" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-48 rounded-lg" />
        <Skeleton className="h-48 rounded-lg" />
        <Skeleton className="h-48 rounded-lg" />
        <Skeleton className="h-48 rounded-lg" />
      </div>
      <div className="flex items-center gap-2 text-sm text-stone-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Generating today&apos;s brief
      </div>
    </div>
  );
}

function toItems(values: Array<Record<string, unknown>> | undefined): BriefItem[] {
  return (values || []).map((value) => toItem(value)).filter((item): item is BriefItem => Boolean(item.title));
}

function toItem(value: Record<string, unknown> | undefined, fallbackTitle = ""): BriefItem {
  if (!value) return { title: fallbackTitle };
  return {
    type: asString(value.type),
    title: asString(value.title) || fallbackTitle,
    detail: asString(value.detail) || asString(value.description) || asString(value.reason),
    href: asString(value.href) || null,
    priority: asString(value.priority),
    source: asString(value.source),
  };
}

function toDailyContent(brief: DailyBriefSnapshot | null): DailyContent {
  return {
    briefDate: brief?.briefDate || new Date().toISOString(),
    currentMission: brief?.currentMission || {},
    currentFocus: brief?.currentFocus || {},
    whatChanged: brief?.whatChanged || brief?.recentProgress || [],
    whatMattersToday: brief?.whatMattersToday || [],
    openLoops: brief?.openLoops || [],
    recommendedNextStep: brief?.recommendedNextStep || {},
    focusForToday: brief?.focusForToday || brief?.recommendedNextStep || {},
    recentDecisions: brief?.recentDecisions || [],
    upcomingPriorities: brief?.upcomingPriorities || brief?.whatMattersToday || [],
    updatedAt: brief?.updatedAt,
    createdAt: brief?.createdAt,
  };
}

function asString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function formatBriefDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Today";
  return date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

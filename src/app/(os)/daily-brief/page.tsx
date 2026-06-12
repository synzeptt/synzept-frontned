"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Brain,
  CalendarDays,
  CheckCircle2,
  Clock3,
  FolderKanban,
  ListChecks,
  RefreshCw,
  Sparkles,
  Target,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ProGate } from "@/components/pro/pro-gate";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type DailyBriefSnapshot } from "@/lib/api";
import { sampleDailyBrief } from "@/lib/sample-data";
import { PageFrame } from "@frontend/components/layout/page-frame";

type BriefItem = {
  type?: string;
  title: string;
  detail?: string;
  href?: string | null;
  priority?: string;
  source?: string;
};

type BriefContent = {
  briefDate: string;
  updatedAt?: string | null;
  createdAt?: string | null;
  recommendedNextStep: Record<string, unknown>;
  whatMattersToday: Array<Record<string, unknown>>;
  openLoops: Array<Record<string, unknown>>;
  recentProgress: Array<Record<string, unknown>>;
  projectsNeedingAttention: Array<Record<string, unknown>>;
  contextToRemember: Array<Record<string, unknown>>;
};

const sections = [
  {
    key: "whatMattersToday" as const,
    title: "What Matters Today",
    question: "What is most important today?",
    empty: "Add projects, tasks, or notes and Synzept will identify today's priorities.",
    icon: Target,
  },
  {
    key: "openLoops" as const,
    title: "Open Loops",
    question: "What am I forgetting?",
    empty: "No unfinished loops need attention right now.",
    icon: ListChecks,
  },
  {
    key: "recentProgress" as const,
    title: "Recent Progress",
    question: "What progress have I made recently?",
    empty: "Progress will appear as tasks, notes, projects, and timeline events change.",
    icon: CheckCircle2,
  },
  {
    key: "projectsNeedingAttention" as const,
    title: "Projects Needing Attention",
    question: "What needs my attention?",
    empty: "Active projects have enough focus for now.",
    icon: FolderKanban,
  },
  {
    key: "contextToRemember" as const,
    title: "Context To Remember",
    question: "What should I keep in mind today?",
    empty: "Important reminders and decisions will appear here.",
    icon: Brain,
  },
];

export default function DailyBriefPage() {
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

  const displayBrief = useMemo(() => toBriefContent(brief), [brief]);
  const nextStep = useMemo(() => toItem(displayBrief.recommendedNextStep, "Choose one meaningful priority for today."), [displayBrief]);
  const generatedAt = displayBrief.updatedAt || displayBrief.createdAt;

  const refresh = () => {
    startRefresh(() => {
      void load(true);
    });
  };

  return (
    <PageFrame
      eyebrow="Synzept Pro"
      title="Daily Brief"
      action={
        <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing || loading}>
          <RefreshCw className={`mr-1.5 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      }
    >
      <ProGate feature="Advanced Daily Brief" description="Daily Brief is a Synzept Pro continuity system that summarizes what matters, open loops, recent progress, and your recommended next step.">
      <div className="mx-auto max-w-5xl space-y-4 p-4 pb-24 md:p-7">
        <RecoveryBanner message={error} onRetry={() => load()} />
        {loading ? (
          <BriefSkeleton />
        ) : (
          <>
            <header className="rounded-lg border border-stone-900 bg-stone-950 p-5 text-white shadow-soft md:p-6">
              <div className="flex flex-wrap items-center gap-2 text-xs font-medium uppercase text-stone-400">
                <CalendarDays className="h-3.5 w-3.5" />
                <span>{formatBriefDate(displayBrief.briefDate)}</span>
                <span className="text-stone-600">/</span>
                <span>{brief ? "Generated daily" : "Starter example"}</span>
              </div>
              <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
                <div>
                  <p className="flex items-center gap-2 text-sm font-medium text-stone-300">
                    <Sparkles className="h-4 w-4" />
                    Recommended Next Step
                  </p>
                  <h2 className="mt-2 text-2xl font-semibold leading-8 md:text-3xl">{nextStep.title}</h2>
                  <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-300">{nextStep.detail || "This is the clearest continuation point in your workspace."}</p>
                </div>
                <Link
                  href={nextStep.href || "/dashboard"}
                  className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-white px-4 text-sm font-medium text-stone-950 transition hover:bg-stone-100"
                >
                  Continue
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </header>

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="space-y-4">
                {sections.slice(0, 4).map((section) => (
                  <BriefSection
                    key={section.key}
                    title={section.title}
                    question={section.question}
                    empty={section.empty}
                    icon={section.icon}
                    items={toItems(displayBrief[section.key])}
                  />
                ))}
              </div>
              <aside className="space-y-4">
                <TenSecondRead brief={displayBrief} />
                <BriefSection
                  title={sections[4].title}
                  question={sections[4].question}
                  empty={sections[4].empty}
                  icon={sections[4].icon}
                  items={toItems(displayBrief.contextToRemember)}
                  compact
                />
                <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
                  <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
                    <Clock3 className="h-4 w-4 text-muted" />
                    Brief Status
                  </p>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">
                    {generatedAt ? `Last refreshed ${formatTime(generatedAt)}.` : "Generated for today."}
                  </p>
                </section>
              </aside>
            </div>
          </>
        )}
      </div>
      </ProGate>
    </PageFrame>
  );
}

function TenSecondRead({ brief }: { brief: BriefContent }) {
  const matters = brief.whatMattersToday.length;
  const loops = brief.openLoops.length;
  const projects = brief.projectsNeedingAttention.length;
  return (
    <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <p className="text-sm font-semibold text-stone-950">10 Second Read</p>
      <div className="mt-3 grid grid-cols-3 gap-2">
        <BriefStat label="Priorities" value={matters} />
        <BriefStat label="Loops" value={loops} />
        <BriefStat label="Projects" value={projects} />
      </div>
      <p className="mt-3 text-sm leading-6 text-muted-foreground">
        Start with the recommended next step, then scan open loops before opening new work.
      </p>
    </section>
  );
}

function BriefStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-stone-50 px-2 py-3 text-center">
      <p className="text-xl font-semibold text-stone-950">{value}</p>
      <p className="mt-1 text-[11px] text-muted-foreground">{label}</p>
    </div>
  );
}

function BriefSection({
  title,
  question,
  items,
  empty,
  icon: Icon,
  compact = false,
}: {
  title: string;
  question: string;
  items: BriefItem[];
  empty: string;
  icon: React.ComponentType<{ className?: string }>;
  compact?: boolean;
}) {
  return (
    <section className="rounded-lg border border-border bg-white p-4 shadow-soft md:p-5">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-stone-100">
          <Icon className="h-4 w-4 text-stone-700" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-stone-950">{title}</h3>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">{question}</p>
        </div>
      </div>
      <div className="mt-4 space-y-2">
        {items.slice(0, compact ? 4 : 6).map((item) => (
          <BriefRow key={`${title}-${item.title}`} item={item} />
        ))}
        {!items.length && <p className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </section>
  );
}

function BriefRow({ item }: { item: BriefItem }) {
  const content = (
    <>
      <div className="min-w-0">
        <p className="line-clamp-2 text-sm font-medium leading-5 text-stone-900">{item.title}</p>
        {item.detail ? <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p> : null}
      </div>
      <PriorityPill priority={item.priority} />
    </>
  );

  if (item.href) {
    return (
      <Link href={item.href} className="flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-3 transition hover:bg-stone-100">
        {content}
      </Link>
    );
  }
  return <div className="flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-3">{content}</div>;
}

function PriorityPill({ priority }: { priority?: string }) {
  if (!priority || priority === "medium") return null;
  return (
    <span className={`mt-0.5 shrink-0 rounded-md px-2 py-1 text-[11px] capitalize ${priority === "high" ? "bg-amber-50 text-amber-800" : "bg-stone-100 text-stone-600"}`}>
      {priority}
    </span>
  );
}

function BriefSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-52 rounded-lg" />
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-4">
          <Skeleton className="h-52 rounded-lg" />
          <Skeleton className="h-52 rounded-lg" />
        </div>
        <Skeleton className="h-64 rounded-lg" />
      </div>
    </div>
  );
}

function toItems(values: Array<Record<string, unknown>> | undefined): BriefItem[] {
  return (values || [])
    .map((value) => toItem(value))
    .filter((item): item is BriefItem => Boolean(item.title));
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

function toBriefContent(brief: DailyBriefSnapshot | null): BriefContent {
  if (brief && hasBriefContent(brief)) return brief;
  return {
    briefDate: new Date().toISOString(),
    updatedAt: null,
    createdAt: null,
    recommendedNextStep: sampleDailyBrief.recommendedNextStep,
    whatMattersToday: sampleDailyBrief.whatMattersToday,
    openLoops: sampleDailyBrief.openLoops,
    recentProgress: sampleDailyBrief.recentProgress,
    projectsNeedingAttention: sampleDailyBrief.projectsNeedingAttention,
    contextToRemember: sampleDailyBrief.contextToRemember,
  };
}

function hasBriefContent(brief: DailyBriefSnapshot) {
  return Boolean(
    brief.whatMattersToday.length ||
      brief.openLoops.length ||
      brief.recentProgress.length ||
      brief.projectsNeedingAttention.length ||
      brief.contextToRemember.length ||
      Object.keys(brief.recommendedNextStep || {}).length,
  );
}

function asString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function formatBriefDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Today";
  return date.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

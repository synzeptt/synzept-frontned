"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowRight, CheckCircle2, CircleDot, Loader2, Sparkles, Target, Undo2 } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { api, type Dashboard, type S1Home } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";

export function DashboardPage() {
  const router = useRouter();
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const user = useAuthStore((state) => state.user);
  const [s1Home, setS1Home] = useState<S1Home | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setS1Home(await api.getS1Home());
    } catch {
      try {
        const legacyDashboard = await api.getDashboard();
        setDashboard(legacyDashboard);
      } catch {
        setError("Home could not refresh. You can still continue in Chat.");
      }
    } finally {
      setLoading(false);
    }
  }, [setDashboard, setLoading]);

  useEffect(() => {
    if (s1Home || (dashboard && hasFreshDashboard())) return;
    void load();
  }, [dashboard, hasFreshDashboard, load, s1Home]);

  const home = useMemo(
    () => getHomeContext(dashboard, user?.display_name || null, s1Home),
    [dashboard, user?.display_name, s1Home],
  );

  useEffect(() => {
    if (!s1Home && !dashboard) return;
    void api.trackEvent("s1_home_loaded", "home", {
      open_loops: home.openLoops.length,
      used_s1_context: Boolean(s1Home),
    });
  }, [dashboard, home.openLoops.length, s1Home]);

  const continueWorking = () => {
    localStorage.setItem(CHAT_DRAFT_KEY, s1Home?.continue_prompt || buildMomentPrompt(home));
    void api.trackEvent("s1_continue_clicked", "home", { kind: s1Home ? "s1_home" : "fallback" });
    router.push("/chat");
  };

  return (
    <PageFrame eyebrow="Home" title="Synzept">
      <div className="min-h-full bg-[#f7f6f2] text-stone-950">
        <div className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
          <RecoveryBanner message={error} onRetry={load} className="mb-5" />
          <SynzeptMoment home={home} loading={isLoading && !s1Home && !dashboard} onContinue={continueWorking} />
        </div>
      </div>
    </PageFrame>
  );
}

function SynzeptMoment({ home, loading, onContinue }: { home: HomeContext; loading: boolean; onContinue: () => void }) {
  return (
    <section className="space-y-4 sm:space-y-5">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <div className="rounded-lg border border-stone-200 bg-white p-5 shadow-[0_18px_48px_rgba(32,31,28,0.07)] sm:p-6 lg:p-7">
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-sm font-medium text-stone-500">{home.greeting}</p>
            {loading ? <LoadingPill /> : <SourcePill count={home.sourceCount} />}
          </div>
          <h1 className="mt-3 max-w-3xl text-3xl font-semibold leading-tight tracking-normal text-stone-950 sm:text-4xl lg:text-5xl">{home.welcome}</h1>
          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <SignalCard icon={<Target className="h-4 w-4" />} label="Mission" value={home.mission} href={home.missionIsEmpty ? "/knows-you" : undefined} />
            <SignalCard icon={<CircleDot className="h-4 w-4" />} label="Current Focus" value={home.focus} href={home.focusIsEmpty ? "/knows-you" : undefined} />
          </div>
        </div>

        <aside className="rounded-lg bg-stone-950 p-5 text-white shadow-[0_18px_48px_rgba(32,31,28,0.16)] sm:p-6">
          <div className="flex items-center gap-2 text-stone-400">
            <Sparkles className="h-4 w-4" />
            <p className="text-xs font-medium uppercase tracking-[0.14em]">Suggested Next Action</p>
          </div>
          <h2 className="mt-4 text-2xl font-semibold leading-tight">{home.suggestedAction.title}</h2>
          {home.suggestedAction.reason ? <p className="mt-3 text-sm leading-6 text-stone-300">{home.suggestedAction.reason}</p> : null}
          <button type="button" onClick={onContinue} className="mt-6 inline-flex h-12 w-full items-center justify-center gap-2 rounded-md bg-white px-5 text-sm font-semibold text-stone-950 transition hover:bg-stone-100 sm:w-auto">
            Continue Working
            <ArrowRight className="h-4 w-4" />
          </button>
        </aside>
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.45fr)]">
        <ContextList
          icon={<Undo2 className="h-4 w-4" />}
          label="Open Loops"
          items={home.openLoops}
          emptyTitle="No open loops need attention right now."
          emptyDetail="As you add tasks, project loops, or Knows You notes, they will surface here."
          emptyHref="/tasks"
        />
        <ContextList
          icon={<CheckCircle2 className="h-4 w-4" />}
          label="Continue Working"
          items={home.lastTime}
          emptyTitle="Start a thread or project to create a return point."
          emptyDetail="Synzept will preserve the context once there is something to resume."
          emptyHref="/chat"
          compact
        />
      </div>
    </section>
  );
}

function LoadingPill() {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-stone-100 px-2 py-1 text-xs text-stone-500">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      Restoring context
    </span>
  );
}

function SourcePill({ count }: { count: number }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-[#eef3ed] px-2 py-1 text-xs font-medium text-[#36533f]">
      <Sparkles className="h-3.5 w-3.5" />
      {count ? `${count} signals` : "New workspace"}
    </span>
  );
}

function SignalCard({ icon, label, value, href }: { icon: ReactNode; label: string; value: string; href?: string }) {
  const content = (
    <div className="h-full rounded-lg border border-stone-200 bg-[#fbfbf8] px-4 py-4 transition hover:border-stone-300">
      <div className="flex items-center gap-2 text-stone-400">
        {icon}
        <p className="text-xs font-medium uppercase tracking-[0.14em]">{label}</p>
      </div>
      <p className="mt-3 line-clamp-4 text-lg font-semibold leading-7 text-stone-950">{value}</p>
    </div>
  );

  return href ? (
    <Link href={href} className="block h-full">
      {content}
    </Link>
  ) : content;
}

function ContextList({
  icon,
  label,
  items,
  emptyTitle,
  emptyDetail,
  emptyHref,
  compact = false,
}: {
  icon: ReactNode;
  label: string;
  items: HomeItem[];
  emptyTitle: string;
  emptyDetail: string;
  emptyHref: string;
  compact?: boolean;
}) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-[0_12px_34px_rgba(32,31,28,0.05)] sm:p-5">
      <div className="flex items-center gap-2 text-stone-400">
        {icon}
        <p className="text-xs font-medium uppercase tracking-[0.14em]">{label}</p>
      </div>
      <div className={compact ? "mt-4 space-y-2" : "mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3"}>
        {items.slice(0, compact ? 3 : 5).map((item) => (
          <ContextItem key={`${label}-${item.id || item.title}`} item={item} />
        ))}
        {!items.length ? <EmptyContext title={emptyTitle} detail={emptyDetail} href={emptyHref} /> : null}
      </div>
    </section>
  );
}

function ContextItem({ item }: { item: HomeItem }) {
  const content = (
    <div className="h-full rounded-lg border border-stone-100 bg-[#fbfbf8] px-3 py-3 transition hover:border-stone-300 hover:bg-white">
      <p className="line-clamp-2 text-sm font-semibold leading-5 text-stone-950">{item.title}</p>
      {item.detail ? <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{item.detail}</p> : null}
    </div>
  );

  return item.href ? (
    <Link href={item.href} className="block h-full">
      {content}
    </Link>
  ) : content;
}

function EmptyContext({ title, detail, href }: { title: string; detail: string; href: string }) {
  return (
    <Link href={href} className="block rounded-lg border border-dashed border-stone-300 bg-[#fbfbf8] px-3 py-3 transition hover:border-stone-400 hover:bg-white">
      <p className="text-sm font-semibold text-stone-950">{title}</p>
      <p className="mt-1 text-xs leading-5 text-stone-500">{detail}</p>
    </Link>
  );
}

type HomeItem = { id?: string | null; title: string; detail: string; href?: string | null };
type HomeAction = { title: string; reason: string; href?: string | null };
type HomeContext = {
  greeting: string;
  welcome: string;
  mission: string;
  missionIsEmpty: boolean;
  focus: string;
  focusIsEmpty: boolean;
  openLoops: HomeItem[];
  lastTime: HomeItem[];
  suggestedAction: HomeAction;
  sourceCount: number;
};

function getHomeContext(dashboard: Dashboard | null, displayName: string | null, s1: S1Home | null): HomeContext {
  const os = dashboard?.personal_os;
  const activeProject = dashboard?.projects?.find((project) => project.status === "active") || dashboard?.projects?.[0];
  const mission = s1?.home.mission || cleanText(os?.current_mission) || cleanText(activeProject?.description) || "Add a mission in Synzept Knows You so Home can hold your north star.";
  const focus = s1?.home.focus || cleanText(os?.current_focus) || cleanText(activeProject?.currentFocus) || "Choose the one thing that matters most right now.";
  const openLoops = s1?.home.open_loops.length
    ? s1.home.open_loops.map((item) => ({ id: item.id, title: item.title, detail: item.detail, href: item.href }))
    : (os?.open_loops || []).slice(0, 5).map((item) => ({ id: item.id, title: item.title, detail: item.next_step || item.description || "", href: item.href }));
  const lastTime = s1?.home.last_time.length
    ? s1.home.last_time.map((item) => ({ id: item.id, title: item.title, detail: item.detail, href: item.href }))
    : (dashboard?.continuity_cards || []).slice(0, 3).map((item) => ({ id: item.id, title: item.title, detail: item.description, href: item.href }));
  const fallbackTask = dashboard?.priorities?.[0] || dashboard?.unfinished_tasks?.[0];
  const suggestedAction = s1?.home.suggested_next_action || os?.suggested_next_action || {
    title: fallbackTask?.title || "Choose one meaningful priority for today.",
    reason: fallbackTask?.description || "One clear next move makes this workspace easier to return to.",
    href: "/chat",
  };

  return {
    greeting: s1?.home.greeting || os?.greeting || "Synzept knows where you left off.",
    welcome: `Welcome back${displayName ? `, ${displayName}` : ""}.`,
    mission,
    missionIsEmpty: mission.startsWith("Add a mission"),
    focus,
    focusIsEmpty: focus.startsWith("Choose the one thing"),
    openLoops,
    lastTime,
    suggestedAction,
    sourceCount: Object.values(s1?.context_sources || {}).reduce((total, value) => total + value, 0),
  };
}

function buildMomentPrompt(home: HomeContext) {
  return [
    "Continue working from my Synzept Home.",
    "",
    `Mission: ${home.mission}`,
    `Current Focus: ${home.focus}`,
    `Open Loops: ${home.openLoops.map((item) => item.title).join("; ") || "None visible"}`,
    `Suggested Next Action: ${home.suggestedAction.title}`,
    home.suggestedAction.reason ? `Why: ${home.suggestedAction.reason}` : "",
    "",
    "Do not ask me to re-explain. Help me continue from this context.",
  ].filter(Boolean).join("\n");
}

function cleanText(value: string | null | undefined) {
  return value?.trim() || "";
}

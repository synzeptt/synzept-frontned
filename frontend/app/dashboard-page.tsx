"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { api, type ContinueContext, type ContinueContextCard, type Dashboard, type S1Context } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";
const CONTINUE_PROJECT_KEY = "synzept_continue_project_id";

export function DashboardPage() {
  const router = useRouter();
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const user = useAuthStore((state) => state.user);
  const [continueContext, setContinueContext] = useState<ContinueContext | null>(null);
  const [s1Context, setS1Context] = useState<S1Context | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const context = await api.getS1Context();
      setS1Context(context);
      setContinueContext(context.continue_context);
    } catch {
      try {
        const [legacyDashboard, legacyContinue] = await Promise.all([
          api.getDashboard(),
          api.getContinueContext().catch(() => null),
        ]);
        setDashboard(legacyDashboard);
        setContinueContext(legacyContinue);
      } catch {
        setError("Home could not refresh. You can still continue in Chat.");
      }
    } finally {
      setLoading(false);
    }
  }, [setDashboard, setLoading]);

  useEffect(() => {
    if (s1Context || (dashboard && hasFreshDashboard())) return;
    void load();
  }, [dashboard, hasFreshDashboard, load, s1Context]);

  const home = useMemo(
    () => getHomeContext(dashboard, user?.display_name || null, s1Context),
    [dashboard, user?.display_name, s1Context],
  );

  useEffect(() => {
    if (!s1Context && !dashboard) return;
    void api.trackEvent("s1_home_loaded", "home", {
      open_loops: home.openLoops.length,
      last_activity: home.lastTime.length,
      used_s1_context: Boolean(s1Context),
    });
  }, [dashboard, home.lastTime.length, home.openLoops.length, s1Context]);

  const continueCard = (card: ContinueContextCard) => {
    localStorage.setItem(CHAT_DRAFT_KEY, card.prompt);
    if (card.project_id) localStorage.setItem(CONTINUE_PROJECT_KEY, card.project_id);
    void api.trackEvent("s1_continue_clicked", "home", { card_id: card.id, kind: card.kind });
    router.push("/chat");
  };

  const continueWorking = () => {
    const leadCard = continueContext?.cards?.[0];
    if (leadCard) {
      continueCard(leadCard);
      return;
    }
    localStorage.setItem(CHAT_DRAFT_KEY, buildMomentPrompt(home));
    void api.trackEvent("s1_continue_clicked", "home", { kind: "fallback" });
    router.push("/chat");
  };

  return (
    <PageFrame eyebrow="Home" title="Synzept">
      <div className="min-h-full bg-white text-stone-950">
        <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8 lg:py-10">
          <RecoveryBanner message={error} onRetry={load} className="mb-5" />
          <SynzeptMoment home={home} loading={isLoading && !s1Context && !dashboard} onContinue={continueWorking} />
        </div>
      </div>
    </PageFrame>
  );
}

function SynzeptMoment({ home, loading, onContinue }: { home: HomeContext; loading: boolean; onContinue: () => void }) {
  return (
    <section className="rounded-xl border border-stone-200 bg-[#fbfbf8] p-5 shadow-[0_18px_54px_rgba(32,31,28,0.08)] sm:p-7">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-base font-medium text-stone-500">{home.greeting}</p>
        {loading ? (
          <span className="inline-flex items-center gap-1.5 rounded-md bg-white px-2 py-1 text-xs text-stone-500">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Restoring context
          </span>
        ) : null}
      </div>
      <h1 className="mt-3 max-w-3xl text-4xl font-semibold leading-tight tracking-normal sm:text-5xl">{home.welcome}</h1>

      <div className="mt-7 grid gap-3 md:grid-cols-2">
        <MomentBlock label="Mission" value={home.mission} />
        <MomentBlock label="Current Focus" value={home.focus} />
      </div>

      {home.lastTime.length ? (
        <ContextList label="Last activity" items={home.lastTime} />
      ) : null}
      <ContextList label="Open Loops" items={home.openLoops} empty="No open loops need attention right now." />

      <aside className="mt-6 rounded-xl bg-stone-950 p-5 text-white sm:p-6">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">Suggested Next Action</p>
        <div className="mt-3 grid gap-5 sm:grid-cols-[1fr_auto] sm:items-end">
          <div>
            <h2 className="text-2xl font-semibold leading-tight">{home.suggestedAction.title}</h2>
            {home.suggestedAction.reason ? <p className="mt-2 max-w-2xl text-sm leading-6 text-stone-300">{home.suggestedAction.reason}</p> : null}
          </div>
          <button type="button" onClick={onContinue} className="inline-flex h-12 items-center justify-center gap-2 rounded-md bg-white px-5 text-sm font-semibold text-stone-950 transition hover:bg-stone-100">
            Continue Working
            <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </aside>
    </section>
  );
}

function MomentBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white px-4 py-4">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{label}</p>
      <p className="mt-2 line-clamp-3 text-lg font-semibold leading-7 text-stone-950">{value}</p>
    </div>
  );
}

function ContextList({ label, items, empty }: { label: string; items: HomeItem[]; empty?: string }) {
  return (
    <div className="mt-6">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{label}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {items.slice(0, 3).map((item) => (
          <div key={`${label}-${item.id || item.title}`} className="rounded-lg bg-white px-3 py-3">
            <p className="line-clamp-2 text-sm font-medium text-stone-950">{item.title}</p>
            {item.detail ? <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{item.detail}</p> : null}
          </div>
        ))}
        {!items.length && empty ? <p className="sm:col-span-3 rounded-lg bg-white px-3 py-3 text-sm text-stone-500">{empty}</p> : null}
      </div>
    </div>
  );
}

type HomeItem = { id?: string | null; title: string; detail: string };
type HomeAction = { title: string; reason: string; href?: string | null };
type HomeContext = {
  greeting: string;
  welcome: string;
  mission: string;
  focus: string;
  lastTime: HomeItem[];
  openLoops: HomeItem[];
  suggestedAction: HomeAction;
};

function getHomeContext(dashboard: Dashboard | null, displayName: string | null, s1: S1Context | null): HomeContext {
  const os = dashboard?.personal_os;
  const activeProject = dashboard?.projects?.find((project) => project.status === "active") || dashboard?.projects?.[0];
  const mission = s1?.home.mission || cleanText(os?.current_mission) || cleanText(activeProject?.description) || "Choose a mission Synzept can keep visible.";
  const focus = s1?.home.focus || cleanText(os?.current_focus) || cleanText(activeProject?.currentFocus) || "Choose the next meaningful action.";
  const lastTime = s1?.home.last_time.length
    ? s1.home.last_time.map((item) => ({ id: item.id, title: item.title, detail: item.detail }))
    : (dashboard?.returning_user?.what_changed || dashboard?.recent_activity || []).slice(0, 3).map((item) => ({ id: String(item.id), title: item.title, detail: item.description || "" }));
  const openLoops = s1?.home.open_loops.length
    ? s1.home.open_loops.map((item) => ({ id: item.id, title: item.title, detail: item.detail }))
    : (os?.open_loops || []).slice(0, 3).map((item) => ({ id: item.id, title: item.title, detail: item.next_step || item.description || "" }));
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
    focus,
    lastTime,
    openLoops,
    suggestedAction,
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

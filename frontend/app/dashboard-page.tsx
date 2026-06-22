"use client";

import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Loader2 } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { api, type S1Home } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";

export function DashboardPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const [s1Home, setS1Home] = useState<S1Home | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      setS1Home(await api.getS1Home());
    } catch {
      setError("Home could not refresh. You can still continue in Chat.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const home = useMemo(() => getHomeContext(user?.display_name || null, s1Home), [user?.display_name, s1Home]);

  useEffect(() => {
    if (!s1Home) return;
    void api.trackEvent("s1_home_loaded", "home", {
      open_loops: home.openLoops.length,
      used_s1_context: true,
    });
  }, [home.openLoops.length, s1Home]);

  const continueWorking = () => {
    localStorage.setItem(CHAT_DRAFT_KEY, s1Home?.continue_prompt || buildMomentPrompt(home));
    void api.trackEvent("s1_continue_clicked", "home", { kind: s1Home ? "s1_home" : "default" });
    router.push("/chat");
  };

  return (
    <PageFrame eyebrow="Home" title="Synzept">
      <div className="min-h-full bg-[#f7f6f2] text-stone-950">
        <div className="mx-auto w-full max-w-6xl px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
          <RecoveryBanner message={error} onRetry={load} className="mb-5" />
          <SynzeptMoment home={home} loading={isLoading && !s1Home} onContinue={continueWorking} />
        </div>
      </div>
    </PageFrame>
  );
}

function SynzeptMoment({ home, loading, onContinue }: { home: HomeContext; loading: boolean; onContinue: () => void }) {
  return (
    <section className="space-y-6 sm:space-y-8">
      <div className="rounded-[2rem] bg-white px-6 py-7 shadow-[0_18px_45px_rgba(15,15,15,0.04)] sm:px-8 sm:py-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-stone-500">Home</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-stone-950 sm:text-5xl">{home.greeting}</h1>
        <p className="mt-3 max-w-2xl text-lg leading-8 text-stone-600">{home.subtitle}</p>
        {loading ? <LoadingPill className="mt-6" /> : null}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <HomeCard title="Mission" className="min-h-[220px]">
          <p className="text-xl font-semibold leading-8 text-stone-950">{home.mission}</p>
        </HomeCard>

        <HomeCard title="Next Action" className="min-h-[220px]">
          <div className="flex h-full flex-col justify-between gap-6">
            <div>
              <p className="text-xl font-semibold leading-8 text-stone-950">{home.nextAction.title}</p>
              <p className="mt-3 max-w-lg text-sm leading-6 text-stone-600">{home.nextAction.detail}</p>
            </div>
            <button
              type="button"
              onClick={onContinue}
              className="inline-flex items-center justify-center rounded-2xl bg-stone-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-stone-800 focus:outline-none focus:ring-2 focus:ring-stone-950/30"
            >
              Continue Working
              <ArrowRight className="ml-2 h-4 w-4" />
            </button>
          </div>
        </HomeCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_0.95fr]">
        <HomeCard title={`Open Loops (${home.openLoops.length})`} className="min-h-[280px]">
          {home.openLoops.length ? (
            <ul className="space-y-4">
              {home.openLoops.slice(0, 3).map((loop) => (
                <li key={loop.id ?? loop.title} className="flex items-start gap-3">
                  <span className="mt-2 h-2.5 w-2.5 rounded-full bg-stone-950" />
                  <div>
                    <p className="text-sm font-semibold text-stone-950">{loop.title}</p>
                    {loop.detail ? <p className="mt-1 text-sm leading-6 text-stone-500">{loop.detail}</p> : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm leading-6 text-stone-500">No open loops need attention right now.</p>
          )}
        </HomeCard>

        <HomeCard title="Recent Activity" className="min-h-[280px]">
          {home.recentActivity.length ? (
            <ul className="space-y-4">
              {home.recentActivity.slice(0, 3).map((activity) => (
                <li key={activity.id ?? activity.title}>
                  <p className="text-sm font-semibold text-stone-950">{activity.title}</p>
                  <p className="mt-1 text-sm leading-6 text-stone-500">{activity.subtitle}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm leading-6 text-stone-500">Recent work appears here once Synzept can preserve a return point.</p>
          )}
        </HomeCard>
      </div>

      {home.dailyFocus ? (
        <HomeCard title="Daily Brief Preview" className="bg-[#fafaf7]">
          <p className="text-base leading-7 text-stone-700">{home.dailyFocus}</p>
        </HomeCard>
      ) : null}
    </section>
  );
}

function LoadingPill({ className }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full bg-stone-100 px-4 py-2 text-sm text-stone-500 ${className ?? ""}`}>
      <Loader2 className="h-4 w-4 animate-spin" />
      Restoring context
    </span>
  );
}

function HomeCard({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-[1.75rem] bg-white p-6 ring-1 ring-stone-200/80 shadow-[0_12px_35px_rgba(15,15,15,0.04)] ${className ?? ""}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.26em] text-stone-500">{title}</p>
      <div className="mt-5">{children}</div>
    </section>
  );
}

type HomeItem = { id?: string | null; title: string; detail?: string };
type HomeActivityItem = { id?: string | null; title: string; subtitle: string };
type HomeContext = {
  greeting: string;
  subtitle: string;
  mission: string;
  nextAction: { title: string; detail: string };
  openLoops: HomeItem[];
  recentActivity: HomeActivityItem[];
  dailyFocus?: string;
};

function getHomeContext(displayName: string | null, s1: S1Home | null): HomeContext {
  const mission = s1?.home.mission || "Build Synzept into the AI that knows you.";
  const suggestedAction = s1?.home.suggested_next_action || {
    title: "Choose one meaningful priority for today.",
    reason: "One clear next move makes this workspace easier to return to.",
    href: "/chat",
  };
  const openLoops = s1?.home.open_loops.slice(0, 3).map((loop) => ({
    id: loop.id,
    title: loop.title,
    detail: loop.detail,
  })) || [];
  const recentActivity = s1?.home.last_time.slice(0, 3).map((item) => ({
    id: item.id,
    title: item.title,
    subtitle: item.detail || "Recent activity",
  })) || [];

  return {
    greeting: `Good morning, ${displayName || "there"} 👋`,
    subtitle: "Synzept knows where you left off.",
    mission,
    nextAction: {
      title: suggestedAction.title,
      detail: suggestedAction.reason,
    },
    openLoops,
    recentActivity,
    dailyFocus: s1?.home.focus || undefined,
  };
}

function buildMomentPrompt(home: HomeContext) {
  return [
    "Continue working from my Synzept Home.",
    "",
    `Mission: ${home.mission}`,
    `Current Focus: ${home.dailyFocus || "None"}`,
    `Open Loops: ${home.openLoops.map((item) => item.title).join("; ") || "None visible"}`,
    `Suggested Next Action: ${home.nextAction.title}`,
    home.nextAction.detail ? `Why: ${home.nextAction.detail}` : "",
    "",
    "Do not ask me to re-explain. Help me continue from this context.",
  ]
    .filter(Boolean)
    .join("\n");
}

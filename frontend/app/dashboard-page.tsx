"use client";

import { useCallback, useEffect, useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { ArrowUp, Loader2, MessageSquare } from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Dashboard, type ReturnOpenLoop } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useWorkspaceStore } from "@/stores/workspace";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";

export function DashboardPage() {
  const router = useRouter();
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const user = useAuthStore((state) => state.user);
  const [prompt, setPrompt] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [, startTransition] = useTransition();

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .getDashboard()
      .then((data) => startTransition(() => setDashboard(data)))
      .catch(() => setError("Home could not refresh. You can still continue in Chat."))
      .finally(() => setLoading(false));
  }, [setDashboard, setLoading, startTransition]);

  useEffect(() => {
    if (dashboard && hasFreshDashboard()) return;
    load();
  }, [dashboard, hasFreshDashboard, load]);

  useEffect(() => {
    if (!dashboard) return;
    void api.trackEvent("simple_home_loaded", "home", {
      open_loops: dashboard.personal_os?.open_loops?.length ?? 0,
      active_projects: dashboard.personal_os?.active_projects?.length ?? dashboard.projects?.length ?? 0,
    });
  }, [dashboard]);

  const home = useMemo(() => getHomeContext(dashboard, user?.display_name || null), [dashboard, user?.display_name]);

  const continueInChat = () => {
    const text = prompt.trim() || "Help me continue Synzept.";
    localStorage.setItem(CHAT_DRAFT_KEY, text);
    void api.trackEvent("home_continue_to_chat", "home", { used_custom_prompt: Boolean(prompt.trim()) });
    router.push("/chat");
  };

  return (
    <PageFrame eyebrow="Home" title="Continue">
      <div className="min-h-full bg-[#f7f7f4]">
        <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col px-4 py-8 sm:px-6 md:py-12">
          <RecoveryBanner message={error} onRetry={load} className="mb-4" />
          {isLoading && !dashboard ? (
            <HomeSkeleton />
          ) : (
            <div className="flex flex-1 flex-col justify-center gap-7">
              <section className="space-y-6">
                <div>
                  <p className="text-sm text-stone-500">{home.greeting}</p>
                  <h1 className="mt-3 text-3xl font-semibold leading-tight text-stone-950 sm:text-4xl">Welcome back</h1>
                </div>

                <div className="grid gap-3">
                  <ContextLine label="Current Mission" value={home.mission} />
                  <ContextLine label="Current Focus" value={home.focus} />
                </div>

                <div>
                  <p className="text-sm font-medium text-stone-900">Open Loops</p>
                  <div className="mt-2 space-y-2">
                    {home.openLoops.map((loop) => (
                      <div key={loop.id || loop.title} className="rounded-md border border-stone-200 bg-white px-3 py-3 shadow-sm">
                        <p className="text-sm font-medium text-stone-950">{loop.title}</p>
                        {loop.next_step || loop.description ? (
                          <p className="mt-1 line-clamp-2 text-sm leading-5 text-stone-600">{loop.next_step || loop.description}</p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              </section>

              <section className="rounded-xl border border-stone-200 bg-white p-3 shadow-sm">
                <label htmlFor="continue-input" className="sr-only">
                  What would you like to continue?
                </label>
                <textarea
                  id="continue-input"
                  rows={4}
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      continueInChat();
                    }
                  }}
                  placeholder="What would you like to continue?"
                  className="min-h-32 w-full resize-none rounded-lg border-0 bg-transparent px-2 py-2 text-lg leading-7 text-stone-950 outline-none placeholder:text-stone-400"
                />
                <div className="flex items-center justify-between gap-3 border-t border-stone-100 px-2 pt-3">
                  <p className="hidden text-xs text-stone-500 sm:block">Synzept will bring in memory, goals, projects, and open loops.</p>
                  <button
                    type="button"
                    onClick={continueInChat}
                    className="ml-auto inline-flex h-11 items-center justify-center gap-2 rounded-md bg-stone-950 px-4 text-sm font-medium text-white transition hover:bg-stone-800"
                  >
                    <MessageSquare className="h-4 w-4" />
                    Continue
                    <ArrowUp className="h-4 w-4" />
                  </button>
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </PageFrame>
  );
}

function ContextLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-stone-200 bg-white px-4 py-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{label}</p>
      <p className="mt-2 text-base leading-7 text-stone-950">{value}</p>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-20 rounded-lg" />
      <Skeleton className="h-20 rounded-lg" />
      <Skeleton className="h-40 rounded-lg" />
      <div className="flex items-center gap-2 text-sm text-stone-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Preparing your continuity context
      </div>
    </div>
  );
}

function getHomeContext(dashboard: Dashboard | null, displayName: string | null) {
  const os = dashboard?.personal_os;
  const activeProject = dashboard?.projects?.find((project) => project.status === "active") || dashboard?.projects?.[0];
  const fallbackLoop = dashboard?.priorities?.[0];
  const openLoops: ReturnOpenLoop[] = (os?.open_loops || []).slice(0, 3);

  if (!openLoops.length && fallbackLoop) {
    openLoops.push({
      id: fallbackLoop.id,
      title: fallbackLoop.title,
      description: fallbackLoop.description || "",
      project_id: fallbackLoop.project_id,
      project_name: "Workspace",
      type: "unfinished_task",
      priority: fallbackLoop.priority || "medium",
      href: "/tasks",
      next_step: fallbackLoop.status || "Continue this task.",
    });
  }

  if (!openLoops.length) {
    openLoops.push({
      id: "start",
      title: "Tell Synzept what you want to continue.",
      description: "",
      project_id: null,
      project_name: "Workspace",
      type: "follow_up",
      priority: "medium",
      href: "/chat",
      next_step: "Start with one sentence. The AI will organize the rest.",
    });
  }

  return {
    greeting: os?.greeting || `Good to see you${displayName ? `, ${displayName}` : ""}.`,
    mission: os?.current_mission || activeProject?.description || activeProject?.name || "Create one clear thread for the work that matters now.",
    focus: os?.current_focus || activeProject?.currentFocus || activeProject?.recommendedNextStep || "Start typing and Synzept will help choose the next step.",
    openLoops,
  };
}

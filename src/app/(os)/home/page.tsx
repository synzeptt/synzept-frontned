"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useCallback, useMemo } from "react";
import { ArrowRight, Clock3, Loader2 } from "lucide-react";
import { api, type ActionExecution, type CalendarContext } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { HomeCommandComposer } from "@/components/redesign/home-command-composer";
import { ExecutionTimeline } from "@/components/redesign/execution-timeline";
import { cn } from "@/lib/cn";
import { CommandSurface, Page, SectionHeader } from "@/components/design-system/workspace-primitives";

export default function HomePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeExecutionId, setActiveExecutionId] = useState<string | null>(null);
  const [executions, setExecutions] = useState<ActionExecution[]>([]);
  const [calendar, setCalendar] = useState<CalendarContext | null>(null);
  const [command, setCommand] = useState("");
  const user = useAuthStore((state) => state.user);
  const userName = user?.display_name?.split(" ")[0] || "there";

  // Load executions
  const loadExecutions = useCallback(async () => {
    try {
      const rows = await api.listActionExecutions();
      setExecutions(rows);
    } catch {
      // Handle error silently
    } finally {
    }
  }, []);

  const handleExecutionComplete = useCallback(() => {
    void loadExecutions();
  }, [loadExecutions]);

  useEffect(() => {
    void loadExecutions();
  }, [loadExecutions]);

  useEffect(() => {
    const executionId = searchParams.get("execution");
    if (executionId) setActiveExecutionId(executionId);
  }, [searchParams]);

  useEffect(() => {
    void api.getGoogleCalendarContext().then(setCalendar).catch(() => setCalendar(null));
  }, []);

  // Auto-refresh executions
  useEffect(() => {
    const interval = setInterval(() => void loadExecutions(), 5000);
    return () => clearInterval(interval);
  }, [loadExecutions]);

  const recentWork = useMemo(() => {
    return executions
      .filter((e) => ["completed", "failed"].includes(e.status))
      .sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      .slice(0, 5);
  }, [executions]);

  const activeWork = useMemo(() => executions.filter((execution) => ["queued", "planning", "executing", "running"].includes(execution.status)).slice(0, 3), [executions]);
  const waitingWork = useMemo(() => executions.filter((execution) => ["awaiting_confirmation", "waiting_approval"].includes(execution.status)).slice(0, 3), [executions]);

  return (
    <Page>
      {activeExecutionId ? (
        // EXECUTION VIEW: Full-screen focused on the active task
        <div className="flex flex-col h-[100dvh]">
          <div className="flex-1 overflow-auto">
            <div className="max-w-3xl mx-auto px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
              <ExecutionTimeline
                executionId={activeExecutionId}
                onComplete={handleExecutionComplete}
              />
            </div>
          </div>
          <div className="border-t border-stone-200 bg-white px-4 py-6 sm:px-6">
            <div className="max-w-3xl mx-auto">
              <button
                onClick={() => {
                  setActiveExecutionId(null);
                  router.replace("/home", { scroll: false });
                }}
                className="text-sm font-medium text-stone-600 hover:text-stone-900 transition-colors"
              >
                ← Start something new
              </button>
            </div>
          </div>
        </div>
      ) : (
        // COMMAND VIEW: Focus on getting the next task
        <div className="mx-auto max-w-3xl px-5 py-12 sm:px-8 sm:py-20">
          {/* Greeting */}
          <div className="mb-12 text-center">
            <p className="synzept-eyebrow mb-4">Today · {new Date().toLocaleDateString(undefined, { month: "short", day: "numeric" })}</p>
            <h1 className="text-[2rem] font-semibold leading-[1.14] tracking-[-0.04em] text-stone-950 sm:text-[2.5rem]">
              What can I help you with, {userName}?
            </h1>
            <p className="mx-auto mt-3 max-w-md text-[15px] leading-6 text-stone-600">
              Bring a question, an open loop, or something you want to move forward.
            </p>
          </div>

          {/* Command composer */}
          <section className="mb-14">
            <CommandSurface>
              <HomeCommandComposer
              value={command}
              onValueChange={setCommand}
              onExecuting={(executionId) => {
                setActiveExecutionId(executionId);
                router.replace(`/home?execution=${executionId}`, { scroll: false });
              }}
              />
            </CommandSurface>
          </section>

          {(activeWork.length > 0 || waitingWork.length > 0) && (
            <div className="mb-14 divide-y divide-border/10 border-y border-border/10">
              {activeWork.length > 0 && <WorkSummary title="In progress" icon={<Loader2 className="h-4 w-4 animate-spin" />} items={activeWork} onOpen={setActiveExecutionId} />}
              {waitingWork.length > 0 && <WorkSummary title="Needs your attention" icon={<Clock3 className="h-4 w-4" />} items={waitingWork} onOpen={setActiveExecutionId} />}
            </div>
          )}

          {calendar?.today.length ? <section className="mb-14 border-y border-border/10 py-6"><SectionHeader title="Today" description={`${calendar.today.length} event${calendar.today.length === 1 ? "" : "s"} on your calendar`} action={<Clock3 className="h-4 w-4 text-stone-400" />} /><div className="divide-y divide-border/10">{calendar.today.slice(0, 3).map((event, index) => <div key={`${String(event.title || "event")}-${index}`} className="flex items-center justify-between gap-3 py-3 text-sm"><span className="truncate font-medium text-stone-800">{String(event.title || "Untitled event")}</span><span className="shrink-0 text-xs text-stone-500">{String(event.startAt || event.start || "Time TBD")}</span></div>)}</div></section> : null}

          {recentWork.length > 0 && (
            <div id="recent" className="mt-14 space-y-3">
              <div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">Recently completed</p><button type="button" onClick={() => router.push("/work")} className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-800 hover:text-emerald-950">View all <ArrowRight className="h-3 w-3" /></button></div>
              <div className="space-y-2">
                {recentWork.map((execution) => (
                  <button
                    key={execution.id}
                    type="button"
                    onClick={() => setActiveExecutionId(execution.id)}
                    className="w-full border-b border-border/10 py-4 text-left transition hover:bg-surface-overlay/40"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium text-stone-900">{execution.title}</p>
                      <span className={cn(
                        "shrink-0 text-xs font-medium capitalize",
                        execution.status === "completed" ? "text-green-700" : "text-red-700",
                      )}>
                        {execution.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-stone-500">Open result</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Page>
  );
}

function WorkSummary({ title, icon, items, onOpen }: { title: string; icon: React.ReactNode; items: ActionExecution[]; onOpen: (id: string) => void }) {
  return <section className="py-6"><div className="mb-4 flex items-center gap-2 text-sm font-semibold text-stone-950">{icon}{title}</div><div className="divide-y divide-border/10">{items.map((item) => <button type="button" key={item.id} onClick={() => onOpen(item.id)} className="w-full py-3 text-left transition hover:bg-surface-overlay/40"><div className="flex items-start justify-between gap-3"><span className="min-w-0 truncate text-sm font-medium text-stone-900">{item.title}</span><span className="shrink-0 text-xs text-stone-500">{item.progress}%</span></div><div className="mt-2 h-1 overflow-hidden bg-stone-200"><div className="h-full bg-accent transition-all" style={{ width: `${Math.min(item.progress, 100)}%` }} /></div></button>)}</div></section>;
}


"use client";

import { useEffect, useState } from "react";
import { Compass, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ContextSnapshot } from "@/lib/api";

function text(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export default function ContextEnginePage() {
  const [context, setContext] = useState<ContextSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getContextEngine()
      .then(setContext)
      .catch(() => setError("Context Engine could not load."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const refresh = async () => {
    setRefreshing(true);
    setError(null);
    try {
      setContext(await api.refreshContextEngine());
    } catch {
      setError("Context Engine could not refresh.");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 md:py-10">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <Compass className="mt-1 h-6 w-6 text-stone-900" />
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Phase 6</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Context Engine</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
                The single source of truth for what matters right now.
              </p>
            </div>
          </div>
          <Button size="sm" variant="outline" onClick={refresh} disabled={refreshing}>
            <RefreshCw className="mr-1.5 h-4 w-4" />
            {refreshing ? "Refreshing" : "Refresh"}
          </Button>
        </header>

        <RecoveryBanner message={error} onRetry={load} />

        {loading ? (
          <Skeleton className="h-64 rounded-md" />
        ) : context ? (
          <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Current Focus</h2>
              <p className="mt-3 text-xl font-semibold text-stone-950">{text(context.currentFocus.title, "No current focus set.")}</p>
              <p className="mt-2 text-sm leading-6 text-stone-600">{text(context.currentFocus.detail, "Set a project focus to sharpen continuity.")}</p>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Recommended Next Step</h2>
              <p className="mt-3 text-xl font-semibold text-stone-950">{text(context.recommendedNextStep.title, "Define the next action to keep momentum.")}</p>
              <p className="mt-2 text-sm leading-6 text-stone-600">{text(context.recommendedNextStep.reason)}</p>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Open Loops</h2>
              <div className="mt-3 space-y-2">
                {context.openLoops.map((item, index) => (
                  <div key={`${text(item.id, String(index))}`} className="rounded-md bg-stone-50 px-3 py-2">
                    <p className="text-sm font-medium text-stone-950">{text(item.title, "Untitled loop")}</p>
                    <p className="mt-1 text-xs text-muted">{text(item.projectName)}</p>
                    {text(item.description) && <p className="mt-2 text-sm leading-6 text-stone-600">{text(item.description)}</p>}
                  </div>
                ))}
                {!context.openLoops.length && <p className="text-sm text-muted">No open loops detected.</p>}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Active Themes</h2>
              <div className="mt-3 space-y-2">
                {context.activeThemes.map((item, index) => (
                  <div key={`${text(item.type, "theme")}-${index}`} className="rounded-md bg-stone-50 px-3 py-2">
                    <p className="text-sm font-medium text-stone-950">{text(item.title, "Theme")}</p>
                    <p className="mt-1 text-xs text-muted">{text(item.type)}</p>
                    {text(item.detail) && <p className="mt-2 text-sm leading-6 text-stone-600">{text(item.detail)}</p>}
                  </div>
                ))}
                {!context.activeThemes.length && <p className="text-sm text-muted">No active themes yet.</p>}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 sm:p-5 lg:col-span-2">
              <h2 className="text-sm font-medium text-stone-950">Important Context</h2>
              <div className="mt-3 grid gap-2 md:grid-cols-2">
                {context.importantContext.map((item, index) => (
                  <div key={`${text(item.type, "context")}-${index}`} className="rounded-md bg-stone-50 px-3 py-2">
                    <p className="text-sm font-medium text-stone-950">{text(item.title, "Context")}</p>
                    <p className="mt-1 text-xs text-muted">{text(item.type)}</p>
                    <p className="mt-2 text-sm leading-6 text-stone-600">
                      {typeof item.detail === "string" ? item.detail : JSON.stringify(item.detail)}
                    </p>
                  </div>
                ))}
                {!context.importantContext.length && <p className="text-sm text-muted">No important context yet.</p>}
              </div>
            </section>
          </div>
        ) : null}
      </div>
    </div>
  );
}

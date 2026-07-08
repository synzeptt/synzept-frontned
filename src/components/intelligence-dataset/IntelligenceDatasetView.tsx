"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, Database, GitBranch, Pencil, Play, RotateCcw, ShieldAlert, Sparkles, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { intelligenceDatasetMock } from "@/lib/intelligence-dataset/mock-data";
import type { ReviewItem, SynzeptObject } from "@/lib/intelligence-dataset/types";

export function IntelligenceDatasetView() {
  const [queue, setQueue] = useState<ReviewItem[]>(intelligenceDatasetMock.reviewItems);
  const [approved, setApproved] = useState<SynzeptObject[]>(intelligenceDatasetMock.approvedObjects);
  const [editingId, setEditingId] = useState<string | null>(null);

  const pending = queue.filter((item) => item.status === "pending");
  const rejected = queue.filter((item) => item.status === "rejected");
  const graphNodes = useMemo(() => [...approved], [approved]);

  function approve(item: ReviewItem) {
    setQueue((items) => items.map((candidate) => (candidate.id === item.id ? { ...candidate, status: "approved" } : candidate)));
    setApproved((objects) => (objects.some((object) => object.id === item.object.id) ? objects : [item.object, ...objects]));
  }

  function reject(item: ReviewItem) {
    setQueue((items) => items.map((candidate) => (candidate.id === item.id ? { ...candidate, status: "rejected" } : candidate)));
  }

  function updateTitle(item: ReviewItem, title: string) {
    setQueue((items) => items.map((candidate) => (candidate.id === item.id ? { ...candidate, object: { ...candidate.object, title, updatedAt: "2026-07-08T10:20:00+05:30" } } : candidate)));
  }

  function resetMock() {
    setQueue(intelligenceDatasetMock.reviewItems);
    setApproved(intelligenceDatasetMock.approvedObjects);
    setEditingId(null);
  }

  return (
    <div className="min-h-full bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-muted">
                <Sparkles className="h-4 w-4" />
                Sprint 1 Intelligence Dataset Pipeline
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">Conversation to structured knowledge</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
                Extract goals, decisions, and tasks into a review queue before approved objects become graph nodes.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 lg:w-[480px]">
              <Metric label="Pending" value={pending.length.toString()} />
              <Metric label="Approved" value={approved.length.toString()} />
              <Metric label="Rejected" value={rejected.length.toString()} />
            </div>
          </div>
        </header>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <main className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <h2 className="flex items-center gap-2 text-lg font-semibold">
                    <Play className="h-5 w-5" />
                    Extraction Pipeline
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">{intelligenceDatasetMock.conversation.title}</p>
                </div>
                <Button variant="outline" onClick={resetMock}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Reset mock
                </Button>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {intelligenceDatasetMock.stages.map((stage) => (
                  <article key={stage.name} className="rounded-lg border border-border bg-surface p-4">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-sm font-semibold">{stage.name}</h3>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{stage.objectCount}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{stage.summary}</p>
                    <p className="mt-3 text-xs font-medium uppercase tracking-[0.12em] text-muted">{stage.status}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <ShieldAlert className="h-5 w-5" />
                Pending Queue
              </h2>
              <div className="mt-4 space-y-3">
                {pending.map((item) => (
                  <article key={item.id} className="rounded-lg border border-border bg-surface p-4">
                    <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{item.object.type}</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{item.impact} impact</span>
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{Math.round(item.object.confidence * 100)}%</span>
                        </div>
                        {editingId === item.id ? (
                          <input
                            value={item.object.title}
                            onChange={(event) => updateTitle(item, event.target.value)}
                            className="mt-3 h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none"
                          />
                        ) : (
                          <h3 className="mt-3 text-base font-semibold">{item.object.title}</h3>
                        )}
                        <p className="mt-2 text-sm leading-6 text-zinc-700">{item.object.summary}</p>
                        <p className="mt-3 rounded-md bg-white p-3 text-sm leading-6 text-muted-foreground">{item.rationale}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 lg:justify-end">
                        <Button variant="outline" onClick={() => setEditingId(editingId === item.id ? null : item.id)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Edit
                        </Button>
                        <Button variant="outline" onClick={() => reject(item)}>
                          <XCircle className="mr-2 h-4 w-4" />
                          Reject
                        </Button>
                        <Button onClick={() => approve(item)}>
                          <CheckCircle2 className="mr-2 h-4 w-4" />
                          Approve
                        </Button>
                      </div>
                    </div>
                  </article>
                ))}
                {pending.length === 0 && <p className="rounded-lg bg-surface p-4 text-sm text-muted-foreground">No pending extracted objects.</p>}
              </div>
            </section>
          </main>

          <aside className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Database className="h-5 w-5" />
                Approved Objects
              </h2>
              <div className="mt-3 space-y-3">
                {approved.map((object) => (
                  <article key={object.id} className="rounded-md bg-surface p-3">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-semibold">{object.title}</p>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{object.type}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{object.summary}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <GitBranch className="h-5 w-5" />
                Knowledge Graph
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">{graphNodes.length} approved node(s), {intelligenceDatasetMock.graph.edges.length} relationship edge(s).</p>
              <div className="mt-3 space-y-2">
                {intelligenceDatasetMock.graph.edges.map((edge) => (
                  <div key={edge.id} className="rounded-md bg-surface p-3 text-sm">
                    <p className="font-medium">{edge.type}</p>
                    <p className="mt-1 break-words text-muted-foreground">{edge.sourceId} to {edge.targetId}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <h2 className="text-sm font-semibold text-amber-900">Safety rule</h2>
              <p className="mt-2 text-sm leading-6 text-amber-900">
                High-impact goals and decisions stay in review until the user explicitly approves them.
              </p>
            </section>
          </aside>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">{label}</p>
    </div>
  );
}

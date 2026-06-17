"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, ArrowRight, GitBranch, Network, RefreshCw, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { ProGate } from "@/components/pro/pro-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type GraphAnswer, type RelationshipEdge, type RelationshipGraph, type RelationshipInsight, type RelationshipNode } from "@/lib/api";
import { cn } from "@/lib/cn";

const nodeOrder = ["goal", "project", "task", "person", "decision", "open_loop", "knowledge", "conversation", "timeline_event", "note", "memory", "user"];
const visualLayers = [
  { label: "Goals", types: ["goal"] },
  { label: "Projects", types: ["project"] },
  { label: "Tasks", types: ["task"] },
  { label: "People", types: ["person"] },
  { label: "Decisions", types: ["decision"] },
  { label: "Open Loops", types: ["open_loop"] },
  { label: "Knowledge", types: ["knowledge", "memory", "note", "conversation"] },
];

export default function RelationshipGraphPage() {
  const [graph, setGraph] = useState<RelationshipGraph>({ nodes: [], edges: [] });
  const [insights, setInsights] = useState<RelationshipInsight[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [question, setQuestion] = useState("What is blocking my goal?");
  const [answer, setAnswer] = useState<GraphAnswer | null>(null);
  const [asking, setAsking] = useState(false);

  const nodeById = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node])), [graph.nodes]);
  const selected = selectedId ? nodeById.get(selectedId) || null : graph.nodes[0] || null;
  const visibleNodes = useMemo(
    () => graph.nodes.filter((node) => filter === "all" || node.nodeType === filter),
    [filter, graph.nodes],
  );
  const relatedEdges = useMemo(
    () => graph.edges.filter((edge) => selected && (edge.sourceNodeId === selected.id || edge.targetNodeId === selected.id)),
    [graph.edges, selected],
  );
  const connectedPaths = useMemo(
    () => graph.edges
      .map((edge) => ({ edge, source: nodeById.get(edge.sourceNodeId), target: nodeById.get(edge.targetNodeId) }))
      .filter((item) => item.source && item.target)
      .sort((a, b) => b.edge.strength - a.edge.strength)
      .slice(0, 10),
    [graph.edges, nodeById],
  );
  const counts = useMemo(() => {
    const values = new Map<string, number>();
    graph.nodes.forEach((node) => values.set(node.nodeType, (values.get(node.nodeType) || 0) + 1));
    return values;
  }, [graph.nodes]);

  const load = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const [graphData, insightData] = await Promise.all([
        api.getRelationshipGraph(),
        api.getRelationshipInsights().catch(() => ({ insights: [] })),
      ]);
      setGraph(graphData);
      setInsights(insightData.insights);
      setSelectedId((current) => current || graphData.nodes[0]?.id || null);
    } catch {
      setMessage("Relationship graph could not load.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function refresh() {
    setRefreshing(true);
    setMessage(null);
    try {
      const graphData = await api.refreshRelationshipGraph();
      const insightData = await api.getRelationshipInsights().catch(() => ({ insights: [] }));
      setGraph(graphData);
      setInsights(insightData.insights);
      setSelectedId((current) => current || graphData.nodes[0]?.id || null);
      setMessage("Graph refreshed from current workspace context.");
    } catch {
      setMessage("Graph refresh failed. No relationships were changed.");
    } finally {
      setRefreshing(false);
    }
  }

  async function askGraph() {
    if (!question.trim()) return;
    setAsking(true);
    setMessage(null);
    try {
      setAnswer(await api.answerRelationshipQuestion(question.trim()));
    } catch {
      setMessage("Graph question could not be answered.");
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader label="Relationship Graph" title="What is connected and what matters?" />

      <ProGate feature="Relationship Graph" description="Relationship Graph is a Synzept Pro system that connects goals, projects, memories, decisions, conversations, notes, and timeline events to reveal what matters.">
      <div className="mx-auto max-w-6xl space-y-5 px-4 py-5 md:px-8">
        {message && <p className="rounded-md border border-stone-200 bg-white px-3 py-2 text-sm text-stone-700">{message}</p>}

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
            <div>
              <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
                <Network className="h-4 w-4 text-muted" />
                Connected workspace map
              </p>
              <p className="mt-1 text-sm leading-6 text-muted">
                Projects, goals, tasks, open loops, decisions, notes, memories, conversations, and timeline events are linked so Synzept can surface overlooked context.
              </p>
            </div>
            <Button onClick={refresh} disabled={refreshing}>
              <RefreshCw className={`mr-1.5 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "Refreshing..." : "Refresh Graph"}
            </Button>
          </div>
          <div className="mt-4 grid gap-2 sm:grid-cols-3">
            <Metric label="Entities" value={graph.nodes.length} />
            <Metric label="Relationships" value={graph.edges.length} />
            <Metric label="Discoveries" value={insights.length} />
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <VisualGraph nodes={graph.nodes} edges={graph.edges} selectedId={selected?.id || null} onSelect={setSelectedId} />
          <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
            <p className="text-sm font-semibold text-stone-950">Ask the Graph</p>
            <div className="mt-3 space-y-2">
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                placeholder="What is blocking my goal?"
              />
              <Button onClick={askGraph} disabled={asking || !question.trim()} className="w-full">
                <Search className="mr-1.5 h-4 w-4" />
                {asking ? "Reading graph..." : "Ask"}
              </Button>
            </div>
            {answer && (
              <div className="mt-4 rounded-md bg-stone-50 px-3 py-3">
                <p className="text-sm font-medium text-stone-950">{answer.answer}</p>
                <div className="mt-3 space-y-2">
                  {answer.evidence.slice(0, 4).map((item) => (
                    <button key={`${item.nodeId}-${item.relationshipType}`} onClick={() => setSelectedId(item.nodeId)} className="block w-full rounded-md bg-white px-3 py-2 text-left text-xs leading-5 text-stone-700 hover:bg-stone-100">
                      <span className="font-medium text-stone-950">{item.title}</span>
                      <span className="block text-muted">{item.relationshipType.replace(/_/g, " ")} - {item.reason || item.description}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
        </section>

        <section className="grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)_330px]">
          <div className="rounded-lg border border-border bg-white p-4 shadow-soft">
            <p className="text-sm font-semibold text-stone-950">Entity Types</p>
            <div className="mt-3 space-y-1">
              <FilterButton label="All" value="all" active={filter === "all"} count={graph.nodes.length} onClick={setFilter} />
              {nodeOrder.map((type) => (
                <FilterButton key={type} label={labelForType(type)} value={type} active={filter === type} count={counts.get(type) || 0} onClick={setFilter} />
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-white p-4 shadow-soft">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-stone-950">Connected Entities</p>
              <Badge variant="muted">{visibleNodes.length}</Badge>
            </div>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {loading && <p className="text-sm text-muted">Loading graph...</p>}
              {!loading && visibleNodes.map((node) => (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => setSelectedId(node.id)}
                  className={cn(
                    "min-h-24 rounded-md border px-3 py-3 text-left transition",
                    selected?.id === node.id ? "border-stone-900 bg-stone-50" : "border-stone-200 bg-white hover:bg-stone-50",
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="line-clamp-2 text-sm font-medium text-stone-950">{node.title}</p>
                    <Badge variant={node.nodeType === "open_loop" || node.nodeType === "decision" ? "accent" : "muted"}>{labelForType(node.nodeType)}</Badge>
                  </div>
                  <p className="mt-2 line-clamp-2 text-xs leading-5 text-muted">{node.description || "No description captured."}</p>
                </button>
              ))}
              {!loading && !visibleNodes.length && <p className="text-sm text-muted">Refresh the graph after creating workspace items.</p>}
            </div>
          </div>

          <div className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
                <Search className="h-4 w-4 text-muted" />
                Discovery
              </p>
              <div className="mt-3 space-y-2">
                {insights.slice(0, 5).map((item) => (
                  <button key={`${item.type}-${item.nodeId}`} type="button" onClick={() => setSelectedId(item.nodeId)} className="block w-full rounded-md bg-stone-50 px-3 py-3 text-left transition hover:bg-stone-100">
                    <p className="text-sm font-medium text-stone-950">{item.title}</p>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{item.detail}</p>
                  </button>
                ))}
                {!insights.length && <p className="text-sm leading-6 text-muted">Refresh the graph to discover forgotten connections and hidden dependencies.</p>}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
                <GitBranch className="h-4 w-4 text-muted" />
                Related Work
              </p>
              <div className="mt-3 space-y-2">
                {relatedEdges.slice(0, 5).map((edge) => {
                  const other = edge.sourceNodeId === selected?.id ? nodeById.get(edge.targetNodeId) : nodeById.get(edge.sourceNodeId);
                  return other ? <RelationshipRow key={edge.id} edge={edge} source={selected} target={other} /> : null;
                })}
                {!relatedEdges.length && <p className="text-sm leading-6 text-muted">Select a connected entity to see related work.</p>}
              </div>
            </section>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
            <Activity className="h-4 w-4 text-muted" />
            Relationship Paths
          </p>
          <div className="mt-4 space-y-2">
            {connectedPaths.map(({ edge, source, target }) => (
              <RelationshipRow key={edge.id} edge={edge} source={source} target={target} />
            ))}
            {!connectedPaths.length && <p className="text-sm text-muted">No relationship paths are available yet.</p>}
          </div>
        </section>
      </div>
      </ProGate>
    </div>
  );
}

function RelationshipRow({ edge, source, target }: { edge: RelationshipEdge; source?: RelationshipNode | null; target?: RelationshipNode | null }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <p className="min-w-0 text-sm text-stone-900">
          <span className="font-medium">{source?.title || "Entity"}</span>
          <ArrowRight className="mx-2 inline h-3.5 w-3.5 text-stone-400" />
          <span className="font-medium">{target?.title || "Related entity"}</span>
        </p>
        <Badge variant="muted">{edge.relationshipType.replace(/_/g, " ")}</Badge>
      </div>
      <p className="mt-1 text-xs leading-5 text-muted">{edge.reason || `Strength ${Math.round(edge.strength * 100)}%.`}</p>
    </div>
  );
}

function VisualGraph({
  nodes,
  edges,
  selectedId,
  onSelect,
}: {
  nodes: RelationshipNode[];
  edges: RelationshipEdge[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const edgeCounts = useMemo(() => {
    const counts = new Map<string, number>();
    edges.forEach((edge) => {
      counts.set(edge.sourceNodeId, (counts.get(edge.sourceNodeId) || 0) + 1);
      counts.set(edge.targetNodeId, (counts.get(edge.targetNodeId) || 0) + 1);
    });
    return counts;
  }, [edges]);

  return (
    <section className="overflow-hidden rounded-lg border border-border bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-stone-950">Context Graph</p>
        <Badge variant="muted">Goal to knowledge path</Badge>
      </div>
      <div className="mt-4 overflow-x-auto">
        <div className="grid min-w-[920px] grid-cols-7 gap-3">
          {visualLayers.map((layer, index) => {
            const layerNodes = nodes
              .filter((node) => layer.types.includes(node.nodeType))
              .sort((a, b) => (edgeCounts.get(b.id) || 0) - (edgeCounts.get(a.id) || 0))
              .slice(0, 5);
            return (
              <div key={layer.label} className="relative">
                {index < visualLayers.length - 1 && <div className="absolute left-[calc(100%+0.15rem)] top-10 hidden h-px w-3 bg-stone-200 lg:block" />}
                <p className="mb-2 text-xs font-medium uppercase tracking-[0.12em] text-muted">{layer.label}</p>
                <div className="space-y-2">
                  {layerNodes.map((node) => (
                    <button
                      key={node.id}
                      type="button"
                      onClick={() => onSelect(node.id)}
                      className={cn(
                        "min-h-16 w-full rounded-md border px-2 py-2 text-left text-xs transition",
                        selectedId === node.id ? "border-stone-900 bg-stone-100" : "border-stone-200 bg-stone-50 hover:bg-stone-100",
                      )}
                    >
                      <span className="line-clamp-2 font-medium text-stone-950">{node.title}</span>
                      <span className="mt-1 block text-[11px] text-muted">{edgeCounts.get(node.id) || 0} links</span>
                    </button>
                  ))}
                  {!layerNodes.length && <div className="min-h-16 rounded-md border border-dashed border-stone-200 px-2 py-2 text-xs leading-5 text-muted">No {layer.label.toLowerCase()} yet</div>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FilterButton({ label, value, active, count, onClick }: { label: string; value: string; active: boolean; count: number; onClick: (value: string) => void }) {
  return (
    <button type="button" onClick={() => onClick(value)} className={cn("flex w-full items-center justify-between rounded-md px-3 py-2 text-sm transition", active ? "bg-stone-900 text-white" : "text-stone-700 hover:bg-stone-50")}>
      <span>{label}</span>
      <span className={cn("rounded px-1.5 py-0.5 text-xs", active ? "bg-white/15 text-white" : "bg-stone-100 text-stone-500")}>{count}</span>
    </button>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-3">
      <p className="text-2xl font-semibold text-stone-950">{value}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </div>
  );
}

function labelForType(type: string) {
  return type.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

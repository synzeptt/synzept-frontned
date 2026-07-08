"use client";

import { type PointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Activity, ArrowRight, GitBranch, Network, RefreshCw, Search } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { ProGate } from "@/components/pro/pro-gate";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type GraphAnswer, type RelationshipEdge, type RelationshipGraph, type RelationshipInsight, type RelationshipNode, type RelationshipNeighborhood } from "@/lib/api";
import { cn } from "@/lib/cn";

const nodeOrder = ["goal", "project", "task", "person", "decision", "open_loop", "knowledge", "conversation", "timeline_event", "note", "memory", "user"];

export default function RelationshipGraphPage() {
  const [graph, setGraph] = useState<RelationshipGraph>({ nodes: [], edges: [] });
  const [insights, setInsights] = useState<RelationshipInsight[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [neighborhood, setNeighborhood] = useState<RelationshipNeighborhood | null>(null);
  const [loadingNeighborhood, setLoadingNeighborhood] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [question, setQuestion] = useState("What is blocking my goal?");
  const [answer, setAnswer] = useState<GraphAnswer | null>(null);
  const [asking, setAsking] = useState(false);

  const nodeById = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node])), [graph.nodes]);
  const selected = selectedId ? nodeById.get(selectedId) || null : graph.nodes[0] || null;
  const visibleNodes = useMemo(
    () => graph.nodes.filter((node) => (filter === "all" || node.nodeType === filter) && (!searchQuery.trim() || `${node.title} ${node.description}`.toLowerCase().includes(searchQuery.toLowerCase()))),
    [filter, graph.nodes, searchQuery],
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
  const neighborhoodNodeIds = useMemo(
    () => new Set(neighborhood?.relatedNodes.map((node) => node.id) ?? []),
    [neighborhood],
  );

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

  async function loadNeighborhood(nodeId: string) {
    setLoadingNeighborhood(true);
    try {
      setNeighborhood(await api.getRelationshipNeighborhood(nodeId));
    } catch {
      setMessage("Could not load node neighborhood.");
      setNeighborhood(null);
    } finally {
      setLoadingNeighborhood(false);
    }
  }

  useEffect(() => {
    if (selectedId) {
      loadNeighborhood(selectedId);
    } else {
      setNeighborhood(null);
    }
  }, [selectedId]);

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
          <VisualGraph
            nodes={graph.nodes}
            edges={graph.edges}
            selectedId={selected?.id || null}
            neighborhoodNodeIds={neighborhoodNodeIds}
            onSelect={setSelectedId}
          />
          <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-stone-950">Ask the Graph</p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => selected?.id && loadNeighborhood(selected.id)}
                disabled={!selected || loadingNeighborhood}
              >
                {loadingNeighborhood ? "Loading…" : "Expand neighbors"}
              </Button>
            </div>
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
            <div className="mt-3 space-y-3">
              <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                  placeholder="Search nodes by title or description"
                />
                <Button type="button" variant="outline" onClick={() => setSearchQuery("")}>Clear</Button>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
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
  neighborhoodNodeIds,
  onSelect,
}: {
  nodes: RelationshipNode[];
  edges: RelationshipEdge[];
  selectedId: string | null;
  neighborhoodNodeIds: Set<string>;
  onSelect: (id: string) => void;
}) {
  const canvasRef = useRef<HTMLDivElement | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const layout = useMemo(() => {
    const columns = nodeOrder.filter((type) => nodes.some((node) => node.nodeType === type));
    const positions = new Map<string, { x: number; y: number }>();
    columns.forEach((type, columnIndex) => {
      const items = nodes
        .filter((node) => node.nodeType === type)
        .sort((a, b) => a.title.localeCompare(b.title));
      items.forEach((node, rowIndex) => {
        positions.set(node.id, {
          x: columnIndex * 260 + 120,
          y: rowIndex * 110 + 90,
        });
      });
    });
    const width = Math.max(960, columns.length * 260 + 160);
    const height = Math.max(420, Math.max(...Array.from(positions.values()).map((pos) => pos.y + 120), 0));
    return { positions, width, height, columns };
  }, [nodes]);

  const handlePointerDown = (event: PointerEvent<HTMLDivElement>) => {
    dragStart.current = { x: event.clientX, y: event.clientY };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!dragStart.current) {
      return;
    }
    const deltaX = event.clientX - dragStart.current.x;
    const deltaY = event.clientY - dragStart.current.y;
    dragStart.current = { x: event.clientX, y: event.clientY };
    setOffset((previous) => ({ x: previous.x + deltaX, y: previous.y + deltaY }));
  };

  const handlePointerUp = (event: PointerEvent<HTMLDivElement>) => {
    dragStart.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  };

  const handleWheel = (event: React.WheelEvent<HTMLDivElement>) => {
    event.preventDefault();
    const delta = -event.deltaY / 500;
    setScale((current) => {
      const next = Math.min(2.2, Math.max(0.55, current * (1 + delta)));
      return Number(next.toFixed(3));
    });
  };

  const resetView = () => {
    setScale(1);
    setOffset({ x: 0, y: 0 });
  };

  const selectedNode = selectedId ? nodes.find((node) => node.id === selectedId) : null;

  return (
    <section className="overflow-hidden rounded-lg border border-border bg-white p-4 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-stone-950">Life Graph</p>
          <p className="text-xs text-muted">Drag to pan, scroll to zoom, click a node to focus.</p>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={resetView}>Reset</Button>
          <Badge variant="muted">{nodes.length} entities</Badge>
        </div>
      </div>
      <div
        ref={canvasRef}
        className="mt-4 min-h-[520px] overflow-hidden rounded-lg border border-stone-200 bg-stone-50 shadow-inner"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
        onWheel={handleWheel}
      >
        <svg width="100%" height="520" viewBox={`0 0 ${layout.width} ${layout.height}`} className="block">
          <defs>
            <marker id="arrow" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto" markerUnits="strokeWidth">
              <path d="M0,0 L6,3 L0,6" fill="#94a3b8" />
            </marker>
          </defs>
          <g transform={`translate(${offset.x} ${offset.y}) scale(${scale})`}>
            {layout.columns.map((type, index) => (
              <g key={type}>
                <text x={index * 260 + 120} y={30} textAnchor="middle" className="text-xs font-semibold fill-slate-500">
                  {labelForType(type)}
                </text>
              </g>
            ))}
            {edges.map((edge) => {
              const source = layout.positions.get(edge.sourceNodeId);
              const target = layout.positions.get(edge.targetNodeId);
              if (!source || !target) return null;
              const isHighlighted = selectedId && (edge.sourceNodeId === selectedId || edge.targetNodeId === selectedId);
              return (
                <line
                  key={edge.id}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={isHighlighted ? "#0f766e" : "#94a3b8"}
                  strokeWidth={isHighlighted ? 2.3 : 1.3}
                  opacity={isHighlighted ? 0.9 : 0.45}
                  markerEnd="url(#arrow)"
                />
              );
            })}
            {nodes.map((node) => {
              const position = layout.positions.get(node.id);
              if (!position) return null;
              const isSelected = node.id === selectedId;
              const isNeighbor = neighborhoodNodeIds.has(node.id);
              const fill = isSelected ? "#f8fafc" : isNeighbor ? "#f1f5f9" : "#ffffff";
              const stroke = isSelected ? "#0f766e" : isNeighbor ? "#94a3b8" : "#cbd5e1";
              return (
                <g key={node.id} className="cursor-pointer" onClick={() => onSelect(node.id)}>
                  <rect
                    x={position.x - 90}
                    y={position.y - 26}
                    width={180}
                    height={52}
                    rx={14}
                    fill={fill}
                    stroke={stroke}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                  />
                  <text x={position.x} y={position.y - 4} textAnchor="middle" className="text-xs font-semibold fill-slate-950">
                    {node.title.length > 25 ? `${node.title.slice(0, 24)}…` : node.title}
                  </text>
                  <text x={position.x} y={position.y + 14} textAnchor="middle" className="text-[11px] fill-slate-600">
                    {labelForType(node.nodeType)}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>
      {selectedNode && (
        <div className="mt-4 rounded-lg border border-border bg-stone-50 p-4 text-sm text-stone-700">
          <p className="font-semibold text-stone-950">Focused entity</p>
          <p className="mt-2 text-sm font-medium text-stone-900">{selectedNode.title}</p>
          <p className="mt-1 text-xs leading-5 text-muted">{selectedNode.description || "No description available."}</p>
        </div>
      )}
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

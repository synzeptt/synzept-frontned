"use client";

import { useMemo, useState } from "react";
import { GitBranch, Network, Route, Search } from "lucide-react";
import { cn } from "@/lib/cn";
import { decisionGraphMock } from "@/lib/decision-graph/mock-data";
import type { DecisionGraphEdge, DecisionGraphNode } from "@/lib/decision-graph/types";

const nodeColors: Record<string, string> = {
  decision: "fill-stone-900",
  mission: "fill-indigo-600",
  goal: "fill-emerald-600",
  project: "fill-sky-600",
  people: "fill-violet-600",
  memory: "fill-amber-600",
  conversation: "fill-cyan-700",
  evidence: "fill-lime-700",
  alternative: "fill-orange-600",
  risk: "fill-rose-600",
  outcome: "fill-teal-700",
  lesson: "fill-slate-600",
};

const relationshipLabels: Record<string, string> = {
  all: "All",
  influenced_by: "Influenced by",
  supports: "Supports",
  blocks: "Blocks",
  resulted_in: "Resulted in",
  contradicts: "Contradicts",
  related_to: "Related to",
  reviewed_by: "Reviewed by",
  learned_from: "Learned from",
};

export function DecisionGraphView() {
  const [selectedNodeId, setSelectedNodeId] = useState("decision-memory-feed-home");
  const [relationship, setRelationship] = useState("all");
  const [query, setQuery] = useState("");

  const selectedNode = decisionGraphMock.nodes.find((node) => node.id === selectedNodeId) ?? decisionGraphMock.nodes[0];
  const selectedEdgeIds = useMemo(() => {
    return new Set(decisionGraphMock.edges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id).map((edge) => edge.id));
  }, [selectedNode.id]);

  const visibleEdges = useMemo(() => {
    return decisionGraphMock.edges.filter((edge) => relationship === "all" || edge.relationship === relationship);
  }, [relationship]);

  const visibleNodeIds = useMemo(() => {
    const ids = new Set<string>();
    visibleEdges.forEach((edge) => {
      ids.add(edge.source);
      ids.add(edge.target);
    });
    return ids;
  }, [visibleEdges]);

  const visibleNodes = decisionGraphMock.nodes.filter((node) => visibleNodeIds.has(node.id));
  const filteredNodes = decisionGraphMock.nodes.filter((node) => {
    const q = query.trim().toLowerCase();
    return !q || [node.title, node.description, node.type, node.status, node.importance].filter(Boolean).join(" ").toLowerCase().includes(q);
  });

  const connectedEdges = decisionGraphMock.edges.filter((edge) => edge.source === selectedNode.id || edge.target === selectedNode.id);
  const connectedNodes = connectedEdges
    .map((edge) => decisionGraphMock.nodes.find((node) => node.id === (edge.source === selectedNode.id ? edge.target : edge.source)))
    .filter((node): node is DecisionGraphNode => Boolean(node));

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <main className="space-y-5">
        <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Network className="h-5 w-5" />
                Interactive Graph
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">Explore decisions, context, evidence, alternatives, risks, outcomes, and lessons.</p>
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {["all", ...decisionGraphMock.supportedRelationships].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setRelationship(item)}
                  className={cn(
                    "h-8 shrink-0 rounded-md px-3 text-xs font-medium",
                    relationship === item ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-700 hover:bg-stone-200",
                  )}
                >
                  {relationshipLabels[item] ?? item}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-4 overflow-x-auto rounded-lg border border-border bg-stone-50">
            <svg viewBox="0 0 1040 820" className="h-[620px] min-w-[980px] w-full">
              <defs>
                <marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
                  <path d="M0,0 L0,6 L9,3 z" fill="#78716c" />
                </marker>
              </defs>
              {visibleEdges.map((edge) => {
                const source = nodeById(edge.source);
                const target = nodeById(edge.target);
                if (!source || !target) return null;
                const active = selectedEdgeIds.has(edge.id);
                return (
                  <g key={edge.id}>
                    <line
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={active ? "#1c1917" : "#a8a29e"}
                      strokeWidth={active ? 3 : 1.5}
                      strokeDasharray={edge.relationship === "contradicts" || edge.relationship === "blocks" ? "7 5" : undefined}
                      markerEnd="url(#arrow)"
                    />
                    <text x={(source.x + target.x) / 2} y={(source.y + target.y) / 2 - 8} textAnchor="middle" className="fill-stone-500 text-[11px]">
                      {edge.relationship}
                    </text>
                  </g>
                );
              })}
              {visibleNodes.map((node) => {
                const active = node.id === selectedNode.id;
                return (
                  <g key={node.id} role="button" tabIndex={0} onClick={() => setSelectedNodeId(node.id)} className="cursor-pointer">
                    <circle cx={node.x} cy={node.y} r={active ? 30 : node.type === "decision" ? 26 : 22} className={nodeColors[node.type] ?? "fill-stone-500"} opacity={active ? 1 : 0.9} />
                    <circle cx={node.x} cy={node.y} r={active ? 36 : 28} fill="transparent" stroke={active ? "#1c1917" : "#e7e5e4"} strokeWidth={active ? 3 : 1} />
                    <text x={node.x} y={node.y + 44} textAnchor="middle" className="fill-stone-800 text-[12px] font-medium">
                      {shortLabel(node.title)}
                    </text>
                    <text x={node.x} y={node.y + 60} textAnchor="middle" className="fill-stone-500 text-[10px]">
                      {node.type}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-2">
          <Panel title="Cause-and-effect chains" icon={<Route className="h-5 w-5" />}>
            <div className="space-y-3">
              {decisionGraphMock.chains.map((chain) => (
                <button key={chain.id} type="button" onClick={() => setSelectedNodeId(chain.nodeIds[0])} className="w-full rounded-md bg-surface p-3 text-left hover:bg-stone-100">
                  <p className="text-sm font-semibold">{chain.title}</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{chain.summary}</p>
                  <p className="mt-2 text-xs text-stone-500">{chain.nodeIds.length} nodes / {chain.edgeIds.length} relationships</p>
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="Graph insights" icon={<GitBranch className="h-5 w-5" />}>
            <div className="space-y-3">
              {decisionGraphMock.insights.map((insight) => (
                <article key={insight.id} className="rounded-md bg-surface p-3">
                  <div className="flex items-start justify-between gap-3">
                    <p className="text-sm font-semibold">{insight.title}</p>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs text-stone-700">Impact {insight.impact}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted-foreground">{insight.summary}</p>
                  <p className="mt-2 text-xs text-stone-500">{insight.supportingConnectionIds.length} supporting connections</p>
                </article>
              ))}
            </div>
          </Panel>
        </section>
      </main>

      <aside className="space-y-5">
        <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Find graph node"
              className="h-10 w-full rounded-lg border border-border bg-white pl-9 pr-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
            />
          </label>
          <div className="mt-3 max-h-60 space-y-2 overflow-y-auto">
            {filteredNodes.map((node) => (
              <button key={node.id} type="button" onClick={() => setSelectedNodeId(node.id)} className={cn("w-full rounded-md p-3 text-left", selectedNode.id === node.id ? "bg-stone-900 text-white" : "bg-surface hover:bg-stone-100")}>
                <p className="text-sm font-semibold">{node.title}</p>
                <p className={cn("mt-1 text-xs capitalize", selectedNode.id === node.id ? "text-stone-200" : "text-muted-foreground")}>{node.type}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{selectedNode.type}</p>
          <h2 className="mt-2 text-lg font-semibold">{selectedNode.title}</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">{selectedNode.description}</p>
          <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
            <Info label="Status" value={selectedNode.status ?? "n/a"} />
            <Info label="Importance" value={selectedNode.importance ?? "n/a"} />
            <Info label="Confidence" value={selectedNode.confidence ? `${Math.round(selectedNode.confidence * 100)}%` : "n/a"} />
            <Info label="Connections" value={connectedEdges.length} />
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
          <h2 className="text-lg font-semibold">Connected Context</h2>
          <div className="mt-3 space-y-3">
            {connectedEdges.map((edge) => {
              const other = connectedNodes.find((node) => node.id === (edge.source === selectedNode.id ? edge.target : edge.source));
              return (
                <article key={edge.id} className="rounded-md bg-surface p-3">
                  <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{edge.relationship}</p>
                  <p className="mt-1 text-sm font-semibold">{other?.title ?? edge.target}</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{edge.label}</p>
                  <p className="mt-2 text-xs text-stone-500">Strength {edge.strength} / Evidence {edge.evidence.join(", ")}</p>
                </article>
              );
            })}
          </div>
        </section>
      </aside>
    </div>
  );
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <h2 className="flex items-center gap-2 text-lg font-semibold">{icon}{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Info({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md bg-surface p-2">
      <p className="text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold text-stone-900">{value}</p>
    </div>
  );
}

function nodeById(id: string): DecisionGraphNode | undefined {
  return decisionGraphMock.nodes.find((node) => node.id === id);
}

function shortLabel(label: string): string {
  return label.length > 26 ? `${label.slice(0, 23)}...` : label;
}

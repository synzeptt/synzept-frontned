"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link2, Network, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type RelationshipEdge, type RelationshipGraph, type RelationshipNode } from "@/lib/api";

const nodeTypes: RelationshipNode["nodeType"][] = ["user", "goal", "project", "memory", "decision", "timeline_event"];

export default function RelationshipGraphPage() {
  const [graph, setGraph] = useState<RelationshipGraph>({ nodes: [], edges: [] });
  const [nodeType, setNodeType] = useState<RelationshipNode["nodeType"]>("project");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sourceNodeId, setSourceNodeId] = useState("");
  const [targetNodeId, setTargetNodeId] = useState("");
  const [relationshipType, setRelationshipType] = useState("matters_to");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nodesById = useMemo(() => new Map(graph.nodes.map((node) => [node.id, node])), [graph.nodes]);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .getRelationshipGraph()
      .then(setGraph)
      .catch(() => setError("Relationship Graph could not load."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const createNode = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await api.createRelationshipNode({ nodeType, title: title.trim(), description: description.trim() });
      setGraph((current) => ({ ...current, nodes: [created, ...current.nodes] }));
      setTitle("");
      setDescription("");
    } catch {
      setError("Node could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const createEdge = async (event: FormEvent) => {
    event.preventDefault();
    if (!sourceNodeId || !targetNodeId || sourceNodeId === targetNodeId || !relationshipType.trim()) return;
    setSaving(true);
    setError(null);
    try {
      const created = await api.createRelationshipEdge({
        sourceNodeId,
        targetNodeId,
        relationshipType: relationshipType.trim(),
        reason: reason.trim(),
        strength: 0.7,
      });
      setGraph((current) => ({ ...current, edges: [created, ...current.edges] }));
      setReason("");
    } catch {
      setError("Relationship could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  const deleteNode = async (node: RelationshipNode) => {
    await api.deleteRelationshipNode(node.id);
    setGraph((current) => ({
      nodes: current.nodes.filter((item) => item.id !== node.id),
      edges: current.edges.filter((edge) => edge.sourceNodeId !== node.id && edge.targetNodeId !== node.id),
    }));
  };

  const deleteEdge = async (edge: RelationshipEdge) => {
    await api.deleteRelationshipEdge(edge.id);
    setGraph((current) => ({ ...current, edges: current.edges.filter((item) => item.id !== edge.id) }));
  };

  return (
    <div className="h-full overflow-y-auto bg-[#faf9f7]">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 md:py-10">
        <header className="mb-6 flex items-start gap-3">
          <Network className="mt-1 h-6 w-6 text-stone-900" />
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">Phase 5</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-stone-950">Relationship Graph</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
              Connect the user, goals, projects, memories, decisions, and timeline events so Synzept can explain why work matters.
            </p>
          </div>
        </header>

        <RecoveryBanner message={error} onRetry={load} />

        <div className="grid gap-5 lg:grid-cols-[1fr_1fr]">
          <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
            <h2 className="text-sm font-medium text-stone-950">Add node</h2>
            <form onSubmit={createNode} className="mt-3 grid gap-3">
              <select
                value={nodeType}
                onChange={(event) => setNodeType(event.target.value as RelationshipNode["nodeType"])}
                className="h-10 rounded-lg border border-border bg-white px-3 text-sm outline-none"
              >
                {nodeTypes.map((type) => (
                  <option key={type} value={type}>{type.replace("_", " ")}</option>
                ))}
              </select>
              <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Title" />
              <Input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Why this matters" />
              <Button type="submit" size="sm" disabled={saving}>
                <Plus className="mr-1.5 h-4 w-4" />
                Add Node
              </Button>
            </form>
          </section>

          <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
            <h2 className="text-sm font-medium text-stone-950">Connect nodes</h2>
            <form onSubmit={createEdge} className="mt-3 grid gap-3">
              <select value={sourceNodeId} onChange={(event) => setSourceNodeId(event.target.value)} className="h-10 rounded-lg border border-border bg-white px-3 text-sm outline-none">
                <option value="">Source</option>
                {graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.title}</option>)}
              </select>
              <select value={targetNodeId} onChange={(event) => setTargetNodeId(event.target.value)} className="h-10 rounded-lg border border-border bg-white px-3 text-sm outline-none">
                <option value="">Target</option>
                {graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.title}</option>)}
              </select>
              <Input value={relationshipType} onChange={(event) => setRelationshipType(event.target.value)} placeholder="Relationship type" />
              <Input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Reason" />
              <Button type="submit" size="sm" disabled={saving || graph.nodes.length < 2}>
                <Link2 className="mr-1.5 h-4 w-4" />
                Connect
              </Button>
            </form>
          </section>
        </div>

        {loading ? (
          <Skeleton className="mt-5 h-48 rounded-md" />
        ) : (
          <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Nodes</h2>
              <div className="mt-3 space-y-2">
                {graph.nodes.map((node) => (
                  <div key={node.id} className="flex items-start justify-between gap-3 rounded-md bg-stone-50 px-3 py-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-stone-950">{node.title}</p>
                      <p className="mt-1 text-xs text-muted">{node.nodeType.replace("_", " ")}</p>
                      {node.description && <p className="mt-2 text-sm leading-6 text-stone-600">{node.description}</p>}
                    </div>
                    <Button size="icon" variant="ghost" aria-label="Delete node" onClick={() => deleteNode(node)}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                {!graph.nodes.length && <p className="text-sm text-muted">No relationships yet.</p>}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 sm:p-5">
              <h2 className="text-sm font-medium text-stone-950">Why it matters</h2>
              <div className="mt-3 space-y-2">
                {graph.edges.map((edge) => (
                  <div key={edge.id} className="rounded-md bg-stone-50 px-3 py-2">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium text-stone-950">
                        {nodesById.get(edge.sourceNodeId)?.title || "Source"} {"->"} {nodesById.get(edge.targetNodeId)?.title || "Target"}
                      </p>
                      <Button size="icon" variant="ghost" aria-label="Delete relationship" onClick={() => deleteEdge(edge)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="mt-1 text-xs text-muted">{edge.relationshipType} / strength {edge.strength.toFixed(1)}</p>
                    {edge.reason && <p className="mt-2 text-sm leading-6 text-stone-600">{edge.reason}</p>}
                  </div>
                ))}
                {!graph.edges.length && <p className="text-sm text-muted">Connect nodes to explain why they matter.</p>}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

"use client";

import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkspaceStore } from "@/stores/workspace-store";

export default function WorkflowsPage() {
  const workflows = useWorkspaceStore((s) => s.workflows);
  const createWorkflow = useWorkspaceStore((s) => s.createWorkflow);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Workflows</h1>
          <p className="mt-1 text-sm text-muted-foreground">Visual automation pipelines with live execution status.</p>
        </div>
        <Button variant="primary" onClick={() => createWorkflow("Automate research and synthesis.")}>
          <Plus size={16} />
          Generate workflow
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {workflows.map((workflow, i) => (
          <motion.article
            key={workflow.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="surface p-5"
          >
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-semibold">{workflow.name}</h2>
              <span className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">{workflow.category}</span>
            </div>
            <p className="text-sm text-muted-foreground">{workflow.description}</p>
            <div className="relative mt-4 h-48 overflow-hidden rounded-lg border border-border bg-black/30">
              {workflow.edges.map((edge) => {
                const from = workflow.nodes.find((n) => n.id === edge.from);
                const to = workflow.nodes.find((n) => n.id === edge.to);
                if (!from || !to) return null;
                return (
                  <div
                    key={edge.id}
                    className="absolute h-px bg-primary/30"
                    style={{ left: from.x + 80, top: from.y + 20, width: Math.max(40, to.x - from.x - 60) }}
                  />
                );
              })}
              {workflow.nodes.map((node) => (
                <div
                  key={node.id}
                  className="absolute w-28 rounded-md border border-border bg-card p-2 text-xs"
                  style={{ left: node.x, top: node.y }}
                >
                  <div className="text-[10px] uppercase text-primary">{node.type}</div>
                  {node.label}
                </div>
              ))}
            </div>
          </motion.article>
        ))}
      </div>
    </div>
  );
}

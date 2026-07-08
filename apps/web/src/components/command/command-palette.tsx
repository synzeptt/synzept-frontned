"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Command, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { useWorkspaceStore } from "@/stores/workspace-store";

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const router = useRouter();
  const searchWorkspace = useWorkspaceStore((s) => s.searchWorkspace);
  const createTask = useWorkspaceStore((s) => s.createTask);
  const createProject = useWorkspaceStore((s) => s.createProject);

  const actions = useMemo(
    () => [
      { label: "Open chat", run: () => router.push("/app/chat") },
      { label: "Open dashboard", run: () => router.push("/app") },
      { label: "New project", run: () => createProject("New Project") },
      { label: "Start research task", run: () => createTask("Research a topic and create an executive brief.") }
    ],
    [router, createProject, createTask]
  );

  const results = query.trim() ? searchWorkspace(query) : [];

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 px-4 pt-[15vh] backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            className="w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-card shadow-2xl"
            initial={{ scale: 0.96, y: -8 }}
            animate={{ scale: 1, y: 0 }}
            exit={{ scale: 0.96, y: -8 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-3 border-b border-border px-4 py-3">
              <Command size={16} className="text-primary" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search workspace, run commands..."
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              />
              <Search size={16} className="text-muted-foreground" />
            </div>
            <div className="max-h-80 overflow-y-auto p-2">
              {results.length > 0 ? (
                results.map((r) => (
                  <button
                    key={`${r.type}-${r.id}`}
                    type="button"
                    className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-secondary"
                    onClick={onClose}
                  >
                    <div className="font-medium">{r.title}</div>
                    <div className="text-xs text-muted-foreground">{r.type} · {r.snippet}</div>
                  </button>
                ))
              ) : (
                actions.map((a) => (
                  <button
                    key={a.label}
                    type="button"
                    className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-secondary"
                    onClick={() => {
                      a.run();
                      onClose();
                    }}
                  >
                    {a.label}
                  </button>
                ))
              )}
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

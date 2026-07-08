"use client";

import { Command, X, Zap } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { workspaceOSMock } from "@/lib/workspace-os/mock-data";

export function CommandBar({ inline = false }: { inline?: boolean }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [lastRun, setLastRun] = useState<string | null>(null);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const commands = useMemo(() => {
    const q = query.trim().toLowerCase();
    return workspaceOSMock.commands.filter((command) => !q || [command.title, command.description, command.category].join(" ").toLowerCase().includes(q));
  }, [query]);

  const trigger = (
    <button
      type="button"
      onClick={() => setOpen(true)}
      className="flex h-10 items-center gap-2 rounded-lg border border-border bg-white px-3 text-sm font-medium text-stone-700 hover:bg-stone-50"
    >
      <Command className="h-4 w-4" />
      Command
      <span className="hidden rounded bg-stone-100 px-1.5 py-0.5 text-[11px] text-stone-500 sm:inline">Ctrl K</span>
    </button>
  );

  return (
    <>
      {inline ? trigger : <div className="fixed bottom-20 right-3 z-40 md:bottom-4">{trigger}</div>}
      {open && (
        <div className="fixed inset-0 z-[80] bg-stone-950/20 p-3 backdrop-blur-sm">
          <div className="mx-auto mt-12 max-w-2xl rounded-lg border border-border bg-white shadow-soft">
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4" />
                <p className="text-sm font-semibold">Universal Command Bar</p>
              </div>
              <button type="button" onClick={() => setOpen(false)} className="grid h-8 w-8 place-items-center rounded-md hover:bg-stone-100" aria-label="Close command bar">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-4">
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Create a mission, find a decision, ask Synzept..."
                className="h-11 w-full rounded-lg border border-border px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
              />
              <div className="mt-3 space-y-2">
                {commands.map((command) => (
                  <button
                    key={command.id}
                    type="button"
                    onClick={() => {
                      setLastRun(`${command.title} queued in mock mode`);
                      setOpen(false);
                    }}
                    className="flex w-full items-start justify-between gap-3 rounded-lg border border-border bg-surface p-3 text-left hover:bg-stone-100"
                  >
                    <span>
                      <span className="block text-sm font-semibold text-stone-950">{command.title}</span>
                      <span className="mt-1 block text-sm leading-6 text-muted-foreground">{command.description}</span>
                    </span>
                    <span className="rounded-full bg-white px-2.5 py-1 text-xs text-stone-600">{command.category}</span>
                  </button>
                ))}
              </div>
              {lastRun && <p className="mt-3 rounded-md bg-stone-100 px-3 py-2 text-sm text-stone-700">{lastRun}</p>}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

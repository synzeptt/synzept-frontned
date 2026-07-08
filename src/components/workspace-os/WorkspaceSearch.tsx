"use client";

import { Search, X } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { cn } from "@/lib/cn";
import { workspaceOSMock } from "@/lib/workspace-os/mock-data";

const filters = ["all", "conversation", "memory", "project", "task", "file", "decision", "people", "mission"];

export function WorkspaceSearch({ compact = false }: { compact?: boolean }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [open, setOpen] = useState(false);

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    return workspaceOSMock.searchIndex.filter((item) => {
      const haystack = [item.title, item.snippet, item.source, ...item.tags].join(" ").toLowerCase();
      const matchesQuery = !q || haystack.includes(q);
      const matchesFilter = filter === "all" || item.type === filter;
      return matchesQuery && matchesFilter;
    }).slice(0, 8);
  }, [filter, query]);

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex h-10 w-full items-center gap-2 rounded-lg border border-border bg-white px-3 text-left text-sm text-muted-foreground hover:bg-stone-50"
      >
        <Search className="h-4 w-4" />
        Search workspace
        {open && <SearchDialog query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} results={results} onClose={() => setOpen(false)} />}
      </button>
    );
  }

  return <SearchPanel query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} results={results} />;
}

function SearchDialog({
  query,
  setQuery,
  filter,
  setFilter,
  results,
  onClose,
}: {
  query: string;
  setQuery: (value: string) => void;
  filter: string;
  setFilter: (value: string) => void;
  results: typeof workspaceOSMock.searchIndex;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[70] bg-stone-950/20 p-3 backdrop-blur-sm" onClick={(event) => event.stopPropagation()}>
      <div className="mx-auto mt-12 max-w-3xl rounded-lg border border-border bg-white shadow-soft">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <p className="text-sm font-semibold">Global Search</p>
          <button type="button" onClick={onClose} className="grid h-8 w-8 place-items-center rounded-md hover:bg-stone-100" aria-label="Close search">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[75vh] overflow-y-auto p-4">
          <SearchPanel query={query} setQuery={setQuery} filter={filter} setFilter={setFilter} results={results} onResultClick={onClose} />
        </div>
      </div>
    </div>
  );
}

function SearchPanel({
  query,
  setQuery,
  filter,
  setFilter,
  results,
  onResultClick,
}: {
  query: string;
  setQuery: (value: string) => void;
  filter: string;
  setFilter: (value: string) => void;
  results: typeof workspaceOSMock.searchIndex;
  onResultClick?: () => void;
}) {
  return (
    <div className="space-y-3">
      <label className="relative block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search conversations, memories, projects, tasks, files, decisions, people, missions"
          className="h-11 w-full rounded-lg border border-border bg-white pl-9 pr-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
        />
      </label>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {filters.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setFilter(item)}
            className={cn(
              "h-8 shrink-0 rounded-md px-3 text-xs font-medium capitalize",
              filter === item ? "bg-stone-900 text-white" : "bg-stone-100 text-stone-700 hover:bg-stone-200",
            )}
          >
            {item}
          </button>
        ))}
      </div>
      <div className="space-y-2">
        {results.map((result) => (
          <Link key={result.id} href={result.href} onClick={onResultClick} className="block rounded-lg border border-border bg-surface p-3 hover:bg-stone-100">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-stone-950">{result.title}</p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{result.snippet}</p>
              </div>
              <span className="rounded-full bg-white px-2.5 py-1 text-xs capitalize text-stone-600">{result.type}</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

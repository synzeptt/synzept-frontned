"use client";

import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, Clock3, PencilLine, Sparkles, TimerReset } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export type PreparedArtifact = {
  id: string;
  title: string;
  type: string;
  status: "Draft" | "Ready to review" | "Reviewed" | "Approved" | "Prepared" | "Waiting";
  createdAt: string;
  updatedAt: string | null;
  sourceContext: string;
  content: string;
  tags: string[];
  timeSavedMinutes?: number;
  sourceType?: "note" | "task";
  sourceId?: string;
  outcomes?: string[];
  ctaLabel?: string;
};

type PreparedArtifactsProps = {
  artifacts: PreparedArtifact[];
  onRefresh?: () => void;
};

export function PreparedArtifacts({ artifacts, onRefresh }: PreparedArtifactsProps) {
  const [selected, setSelected] = useState<PreparedArtifact | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState<"save" | "approve" | null>(null);
  const [localArtifacts, setLocalArtifacts] = useState(artifacts);

  useEffect(() => {
    setLocalArtifacts(artifacts);
  }, [artifacts]);

  const visibleArtifacts = useMemo(() => localArtifacts.slice(0, 4), [localArtifacts]);
  const weeklyTimeSaved = useMemo(() => visibleArtifacts.reduce((sum, artifact) => sum + (artifact.timeSavedMinutes || 0), 0), [visibleArtifacts]);

  const openArtifact = (artifact: PreparedArtifact) => {
    setSelected(artifact);
    setDraft(artifact.content);
  };

  const saveArtifact = async () => {
    if (!selected) return;
    setBusy("save");
    try {
      if (selected.sourceType === "task") {
        await api.updateTask(selected.sourceId ?? selected.id, { title: selected.title, description: draft });
      } else {
        await api.updateNote(selected.sourceId ?? selected.id, { title: selected.title, content: draft });
      }
      setLocalArtifacts((current) => current.map((artifact) => artifact.id === selected.id ? { ...artifact, content: draft, updatedAt: new Date().toISOString() } : artifact));
      onRefresh?.();
    } finally {
      setBusy(null);
    }
  };

  const approveArtifact = async () => {
    if (!selected) return;
    setBusy("approve");
    try {
      const tags = Array.from(new Set([...(selected.tags || []), "reviewed"]));
      if (selected.sourceType === "task") {
        await api.updateTask(selected.sourceId ?? selected.id, { title: selected.title, description: draft });
      } else {
        await api.updateNote(selected.sourceId ?? selected.id, { title: selected.title, content: draft, tags });
      }
      setLocalArtifacts((current) => current.map((artifact) => artifact.id === selected.id ? { ...artifact, status: "Reviewed" as const, tags, content: draft, updatedAt: new Date().toISOString() } : artifact));
      onRefresh?.();
    } finally {
      setBusy(null);
    }
  };

  const actionLabel = (artifact: PreparedArtifact) => {
    if (artifact.ctaLabel) return artifact.ctaLabel;
    if (/email/i.test(artifact.type)) return "Edit";
    if (/review/i.test(artifact.type)) return "Approve";
    if (/meeting/i.test(artifact.type)) return "Review";
    return "Open";
  };

  return (
    <section id="prepared-work" className="rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-[0_8px_24px_rgba(28,25,23,.03)] sm:p-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">Ready now</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">Prepared for you</h2>
        </div>
        <div className="inline-flex items-center gap-2 rounded-full border border-[#dce5de] bg-[#f7faf7] px-3 py-1 text-sm font-medium text-stone-700">
          <TimerReset className="h-4 w-4 text-[#58705f]" />
          <span>{weeklyTimeSaved} min saved</span>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {visibleArtifacts.length ? visibleArtifacts.map((artifact) => (
          <article key={artifact.id} className="rounded-2xl border border-[#dce5de] bg-[#f9fbf8] p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-400">{artifact.type}</p>
                <h3 className="mt-2 text-lg font-semibold tracking-[-0.02em] text-stone-950">{artifact.title}</h3>
              </div>
              <span className="rounded-full border border-[#dce5de] bg-white px-3 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-[#58705f]">{artifact.status === "Ready to review" ? "Prepared" : artifact.status}</span>
            </div>

            <p className="mt-4 text-sm leading-6 text-stone-600">{artifact.outcomes?.[0] || artifact.sourceContext}</p>

            <div className="mt-4 flex flex-wrap gap-2">
              {(artifact.outcomes || []).slice(0, 3).map((outcome) => (
                <span key={outcome} className="rounded-full border border-[#dce5de] bg-white px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.16em] text-stone-600">
                  {outcome}
                </span>
              ))}
            </div>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-stone-500">
              <span className="inline-flex items-center gap-2"><Clock3 className="h-4 w-4" />{artifact.timeSavedMinutes ? `${artifact.timeSavedMinutes} min saved` : "Ready now"}</span>
              <span className="inline-flex items-center gap-2"><Sparkles className="h-4 w-4" />{artifact.status === "Reviewed" ? "Approved" : artifact.status === "Draft" ? "Draft" : "Prepared"}</span>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <Button type="button" size="sm" onClick={() => openArtifact(artifact)}>
                {actionLabel(artifact)}
              </Button>
            </div>
          </article>
        )) : (
          <div className="rounded-2xl border border-dashed border-[#dce5de] bg-[#fcfdfc] p-6 text-sm leading-6 text-stone-600 md:col-span-2">
            <div className="flex items-center gap-2 font-semibold text-stone-900"><CheckCircle2 className="h-4 w-4 text-[#58705f]" /> Nothing is ready yet</div>
            <p className="mt-3">Synzept is still preparing the next move for you.</p>
          </div>
        )}
      </div>

      {selected ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-stone-950/35 px-4 py-6 backdrop-blur-sm" role="dialog" aria-modal="true" aria-label={`Review ${selected.title}`}>
          <div className="flex max-h-[90vh] w-full max-w-3xl flex-col rounded-[30px] border border-[#dce5de] bg-white p-5 shadow-2xl sm:p-8">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#58705f]">{selected.type}</p>
                <h3 className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-950">{selected.title}</h3>
              </div>
              <button type="button" onClick={() => setSelected(null)} className="rounded-full p-2 text-stone-400 transition hover:bg-stone-100 hover:text-stone-700">✕</button>
            </div>

            <div className="mt-5 flex flex-wrap gap-4 text-sm text-stone-500">
              <span className="inline-flex items-center gap-2"><Clock3 className="h-4 w-4" />Created {formatTime(selected.createdAt)}</span>
              <span className="inline-flex items-center gap-2"><PencilLine className="h-4 w-4" />Updated {formatTime(selected.updatedAt || selected.createdAt)}</span>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="rounded-2xl border border-[#dce5de] bg-[#f9fbf8] p-4">
                <p className="text-sm font-semibold text-stone-900">What is ready</p>
                <div className="mt-4 space-y-4 overflow-auto pr-2 text-sm leading-7 text-stone-700">
                  {renderSections(selected.content)}
                </div>
              </div>

              <div className="rounded-2xl border border-[#dce5de] bg-white p-4">
                <p className="text-sm font-semibold text-stone-900">Make a change</p>
                <textarea value={draft} onChange={(event) => setDraft(event.target.value)} className="mt-4 min-h-[280px] w-full rounded-2xl border border-[#dce5de] bg-[#fcfdfc] p-3 text-sm leading-6 text-stone-700 outline-none focus:border-[#58705f]" />
                <div className="mt-4 flex flex-wrap gap-3">
                  <Button type="button" size="sm" onClick={() => void saveArtifact()} disabled={busy === "save"}>{busy === "save" ? "Saving…" : "Save"}</Button>
                  <Button type="button" variant="ghost" size="sm" onClick={() => void approveArtifact()} disabled={busy === "approve"}>{busy === "approve" ? "Approving…" : "Approve"}</Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function renderSections(content: string) {
  const sections = content.split(/\n(?=## )/g).filter(Boolean);
  if (!sections.length) {
    return <p className="text-stone-600">No structured content available yet.</p>;
  }

  return sections.map((section, index) => {
    const headingMatch = section.match(/^##\s+(.+)/);
    const heading = headingMatch?.[1] || `Section ${index + 1}`;
    const body = section.replace(/^##\s+.+\n?/, "").trim();
    const lines = body.split(/\n/).filter(Boolean);

    return (
      <div key={`${heading}-${index}`}>
        <p className="font-semibold text-stone-900">{heading}</p>
        <div className="mt-2 space-y-2">
          {lines.length ? lines.map((line, lineIndex) => {
            const normalized = line.trim();
            if (!normalized) return null;
            if (normalized.startsWith("- ")) {
              return <li key={`${heading}-${lineIndex}`} className="ml-4 list-disc">{normalized.slice(2)}</li>;
            }
            if (/^\d+\./.test(normalized)) {
              return <li key={`${heading}-${lineIndex}`} className="ml-4 list-decimal">{normalized.replace(/^\d+\.\s*/, "")}</li>;
            }
            return <p key={`${heading}-${lineIndex}`}>{normalized}</p>;
          }) : <p className="text-stone-600">No details yet.</p>}
        </div>
      </div>
    );
  });
}

function formatTime(value?: string | null) {
  if (!value) return "just now";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

"use client";

import { useMemo, useState } from "react";
import { Download, Eye, FolderOpen, History, Info, ShieldCheck, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";

const memoryMock = [
  {
    id: "mem-1",
    title: "Quarterly strategy review notes",
    category: "Meeting",
    confidence: 0.82,
    source: "Conversation with leadership team",
    createdAt: "2026-06-05",
    updatedAt: "2026-06-06",
    relatedEntities: ["Project Atlas", "Q3 OKRs"],
    reason: "Saved because you asked Synzept to remember the meeting conclusion.",
    why: "This memory was created from a summary of the leadership review and the action items discussed.",
    pinned: true,
    ignored: false,
  },
  {
    id: "mem-2",
    title: "User research insights",
    category: "Notes",
    confidence: 0.94,
    source: "Note created by you",
    createdAt: "2026-06-12",
    updatedAt: "2026-06-12",
    relatedEntities: ["Project Beacon", "Customer onboarding"],
    reason: "Saved because your note contained customer feedback and improvement ideas.",
    why: "Synzept recognized this content as a knowledge memory relevant to active projects.",
    pinned: false,
    ignored: false,
  },
  {
    id: "mem-3",
    title: "Pending contract approval",
    category: "Decision",
    confidence: 0.71,
    source: "Conversation with legal",
    createdAt: "2026-06-02",
    updatedAt: "2026-06-08",
    relatedEntities: ["Project Atlas", "Legal review"],
    reason: "Saved because the agreement status affects your project launch timeline.",
    why: "Synzept learned this from a decision item and tracked it as a high-impact open loop.",
    pinned: false,
    ignored: true,
  },
];

const recommendationMock = [
  {
    id: "rec-1",
    title: "Follow up on Project Atlas legal review",
    summary: "A contract approval decision is still pending and could block your launch timeline.",
    confidence: 0.78,
    influencedBy: ["Quarterly strategy review notes", "Pending contract approval"],
    goals: ["Finalize Q3 strategy"],
    projects: ["Project Atlas"],
    recentActivity: ["Updated memory: Pending contract approval", "Reviewed legal guidance"],
  },
  {
    id: "rec-2",
    title: "Share user research findings with the product team",
    summary: "Your recent notes highlight onboarding friction that should be surfaced now.",
    confidence: 0.91,
    influencedBy: ["User research insights"],
    goals: ["Improve activation"],
    projects: ["Project Beacon"],
    recentActivity: ["Created note: User research insights"],
  },
];

const historyMock = [
  { id: "hist-1", event: "Created", description: "Memory created from conversation summary.", date: "2026-06-05" },
  { id: "hist-2", event: "Updated", description: "Confidence score adjusted after review.", date: "2026-06-06" },
  { id: "hist-3", event: "Merged", description: "Merged duplicate strategy memory into a single item.", date: "2026-06-08" },
  { id: "hist-4", event: "Deleted", description: "Ignored an older decision memory after validation.", date: "2026-06-10" },
  { id: "hist-5", event: "Restored", description: "Reopened a memory after its project became active again.", date: "2026-06-13" },
];

const privacyStats = {
  memories: 124,
  projects: 19,
  goals: 13,
  people: 28,
  decisions: 7,
  openLoops: 21,
};

const learningRules = [
  { id: "rule-1", source: "Chats", mode: "Ask before remembering" },
  { id: "rule-2", source: "Notes", mode: "Always remember" },
  { id: "rule-3", source: "Projects", mode: "Ask before remembering" },
  { id: "rule-4", source: "Meetings", mode: "Always remember" },
  { id: "rule-5", source: "Files", mode: "Never remember" },
];

export default function TrustPage() {
  const [selectedMemory, setSelectedMemory] = useState(memoryMock[0]);
  const [search, setSearch] = useState("");

  const filteredMemories = useMemo(
    () => memoryMock.filter((memory) => memory.title.toLowerCase().includes(search.toLowerCase()) || memory.category.toLowerCase().includes(search.toLowerCase())),
    [search],
  );

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader label="Trust" title="Trust & Transparency" />
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 md:px-8">
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-stone-950">Privacy dashboard</p>
                <p className="mt-1 text-sm text-muted">See what Synzept knows, why it knows it, and how to control it.</p>
              </div>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export data
              </Button>
            </div>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              <MetricBlock icon={<ShieldCheck className="h-4 w-4" />} label="Memories" value={privacyStats.memories} />
              <MetricBlock icon={<FolderOpen className="h-4 w-4" />} label="Projects" value={privacyStats.projects} />
              <MetricBlock icon={<Sparkles className="h-4 w-4" />} label="Goals" value={privacyStats.goals} />
              <MetricBlock icon={<Eye className="h-4 w-4" />} label="People" value={privacyStats.people} />
              <MetricBlock icon={<Info className="h-4 w-4" />} label="Decisions" value={privacyStats.decisions} />
              <MetricBlock icon={<History className="h-4 w-4" />} label="Open loops" value={privacyStats.openLoops} />
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <Button variant="default">Rebuild knowledge</Button>
              <Button variant="destructive">Reset understanding</Button>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <p className="text-sm font-semibold text-stone-950">Learning controls</p>
            <p className="mt-1 text-sm text-muted">Choose how Synzept remembers different sources.</p>
            <div className="mt-5 space-y-3">
              {learningRules.map((rule) => (
                <RuleCard key={rule.id} source={rule.source} mode={rule.mode} />
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-stone-950">Memory inspector</p>
                <p className="mt-1 text-sm text-muted">Browse every stored memory and inspect why it exists.</p>
              </div>
              <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search memories" className="max-w-[220px]" />
            </div>
            <div className="mt-5 space-y-3">
              {filteredMemories.map((memory) => (
                <MemoryCard key={memory.id} memory={memory} isSelected={selectedMemory?.id === memory.id} onSelect={() => setSelectedMemory(memory)} />
              ))}
              {!filteredMemories.length && <p className="text-sm text-muted">No memories match your search.</p>}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
            <MemoryDetail memory={selectedMemory} />
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-stone-950">Explainability</p>
              <p className="mt-1 text-sm text-muted">Every recommendation includes the memories and goals behind it.</p>
            </div>
            <Badge variant="muted">Interactive mock</Badge>
          </div>
            <div className="mt-6 space-y-4">
              {recommendationMock.map((recommendation) => (
                <RecommendationCard key={recommendation.id} recommendation={recommendation} />
              ))}
            </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-stone-950">Memory history</p>
              <p className="mt-1 text-sm text-muted">Track every change made to your memories.</p>
            </div>
            <Badge variant="muted">Audit trail</Badge>
          </div>
          <div className="mt-5 divide-y divide-border">
            {historyMock.map((event) => (
              <HistoryEntry key={event.id} event={event} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function MetricBlock({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="rounded-3xl border border-border bg-stone-50 px-4 py-5">
      <div className="flex items-center gap-3 text-stone-700">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-white text-stone-900 shadow-sm">{icon}</span>
        <div>
          <p className="text-xs uppercase tracking-[0.18em] text-muted">{label}</p>
          <p className="mt-2 text-2xl font-semibold text-stone-950">{value}</p>
        </div>
      </div>
    </div>
  );
}

function MemoryCard({ memory, isSelected, onSelect }: { memory: typeof memoryMock[number]; isSelected: boolean; onSelect: () => void }) {
  return (
    <button type="button" onClick={onSelect} className={cn("w-full rounded-2xl border p-4 text-left transition", isSelected ? "border-accent bg-accent/10" : "border-border bg-white hover:border-stone-400 hover:bg-stone-50")}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-stone-950">{memory.title}</p>
          <p className="mt-1 text-xs text-muted">{memory.category}</p>
        </div>
        <Badge variant={memory.pinned ? "accent" : "muted"}>{memory.pinned ? "Pinned" : memory.ignored ? "Ignored" : "Saved"}</Badge>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <Stat label="Confidence" value={`${Math.round(memory.confidence * 100)}%`} />
        <Stat label="Updated" value={memory.updatedAt} />
      </div>
    </button>
  );
}

function MemoryDetail({ memory }: { memory: typeof memoryMock[number] }) {
  return (
    <div className="space-y-5">
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-lg font-semibold text-stone-950">{memory.title}</p>
            <p className="mt-1 text-sm text-muted">{memory.category}</p>
          </div>
          <Badge variant={memory.pinned ? "accent" : memory.ignored ? "muted" : "default"}>{memory.pinned ? "Pinned" : memory.ignored ? "Ignored" : "Live"}</Badge>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Stat label="Confidence" value={`${Math.round(memory.confidence * 100)}%`} />
          <Stat label="Source" value={memory.source} />
          <Stat label="Created" value={memory.createdAt} />
          <Stat label="Updated" value={memory.updatedAt} />
        </div>
      </div>

      <div className="grid gap-2">
        <label className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">Why it was saved</label>
        <p className="rounded-3xl border border-border bg-stone-50 p-4 text-sm text-stone-700">{memory.reason}</p>
      </div>

      <div className="grid gap-2">
        <label className="text-xs font-semibold uppercase tracking-[0.15em] text-muted">Related entities</label>
        <div className="flex flex-wrap gap-2">
          {memory.relatedEntities.map((entity) => (
            <Badge key={entity} variant="muted">{entity}</Badge>
          ))}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <Button variant="default">Edit</Button>
        <Button variant="outline">Merge</Button>
        <Button variant="ghost">Ignore</Button>
        <Button variant="destructive">Delete</Button>
      </div>

      <div className="rounded-3xl border border-border bg-stone-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">Explainability</p>
        <p className="mt-3 text-sm text-stone-700">{memory.why}</p>
      </div>
    </div>
  );
}

function RecommendationCard({ recommendation }: { recommendation: typeof recommendationMock[number] }) {
  return (
    <div className="rounded-3xl border border-border bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-stone-950">{recommendation.title}</p>
          <p className="mt-1 text-sm text-muted">{recommendation.summary}</p>
        </div>
        <Badge variant="accent">{Math.round(recommendation.confidence * 100)}%</Badge>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <DetailRow label="Memories" values={recommendation.influencedBy} />
        <DetailRow label="Goals" values={recommendation.goals} />
        <DetailRow label="Projects" values={recommendation.projects} />
        <DetailRow label="Recent activity" values={recommendation.recentActivity} />
      </div>
    </div>
  );
}

function RuleCard({ source, mode }: { source: string; mode: string }) {
  return (
    <div className="rounded-3xl border border-border bg-stone-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-stone-950">{source}</p>
          <p className="mt-1 text-sm text-muted">Control how this source is remembered.</p>
        </div>
        <Badge variant="default">{mode}</Badge>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {(["Always remember", "Ask before remembering", "Never remember"] as const).map((option) => (
          <Button key={option} variant={option === mode ? "default" : "outline"} size="sm">
            {option}
          </Button>
        ))}
      </div>
    </div>
  );
}

function HistoryEntry({ event }: { event: { id: string; event: string; description: string; date: string } }) {
  return (
    <div className="grid gap-2 py-4 sm:grid-cols-[120px_minmax(0,1fr)]">
      <div className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">{event.date}</div>
      <div>
        <p className="font-medium text-stone-950">{event.event}</p>
        <p className="mt-1 text-sm text-muted">{event.description}</p>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-3xl border border-border bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-[0.18em] text-muted">{label}</p>
      <p className="mt-2 text-sm font-semibold text-stone-950">{value}</p>
    </div>
  );
}

function DetailRow({ label, values }: { label: string; values: string[] }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.18em] text-muted">{label}</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {values.map((value) => (
          <Badge key={value} variant="muted">{value}</Badge>
        ))}
      </div>
    </div>
  );
}

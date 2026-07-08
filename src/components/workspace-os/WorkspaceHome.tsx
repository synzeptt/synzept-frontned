"use client";

import { Bot, CheckCircle2, Clock3, FileText, Lightbulb, ShieldCheck, Target } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { CommandBar } from "@/components/workspace-os/CommandBar";
import { WorkspaceSearch } from "@/components/workspace-os/WorkspaceSearch";
import { workspaceOSMock } from "@/lib/workspace-os/mock-data";

function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

export function WorkspaceHome() {
  const { home, generatedAt, designPrinciples } = workspaceOSMock;

  return (
    <div className="min-h-full bg-stone-50 text-stone-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <p className="text-sm font-medium uppercase tracking-[0.18em] text-muted">Workspace OS</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">{home.currentMission.title}</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">{home.currentMission.currentMilestone}</p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:w-[430px]">
              <WorkspaceSearch compact />
              <CommandBar inline />
            </div>
          </div>
          <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_280px]">
            <div>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Current Mission Progress</span>
                <span className="text-muted-foreground">{home.currentMission.progress}%</span>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-stone-100">
                <div className="h-full rounded-full bg-stone-900" style={{ width: `${home.currentMission.progress}%` }} />
              </div>
              <p className="mt-3 text-sm leading-6 text-stone-700">{home.currentMission.nextStep}</p>
            </div>
            <div className="rounded-md bg-surface p-3 text-sm text-muted-foreground">Updated {formatTime(generatedAt)}</div>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
          <main className="space-y-5">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  <h2 className="text-lg font-semibold">Today&apos;s Focus</h2>
                </div>
              </CardHeader>
              <CardContent className="grid gap-3 md:grid-cols-2">
                {home.todaysFocus.map((focus) => (
                  <article key={focus.title} className="rounded-md border border-border bg-surface p-4">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-sm font-semibold">{focus.title}</h3>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-stone-600">{focus.estimatedTime}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-muted-foreground">{focus.reason}</p>
                  </article>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Bot className="h-5 w-5" />
                  <h2 className="text-lg font-semibold">Agent Workspace</h2>
                </div>
              </CardHeader>
              <CardContent className="grid gap-3 lg:grid-cols-2">
                {home.activeAgents.map((agent) => (
                  <article key={agent.id} className="rounded-md border border-border bg-surface p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-sm font-semibold">{agent.name}</h3>
                        <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">{agent.status}</p>
                      </div>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-stone-600">{agent.approvalsAwaitingUser.length} approvals</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-stone-700">{agent.goal}</p>
                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <MiniList title="Recent activity" items={agent.recentActivity} />
                      <MiniList title="Next steps" items={agent.plannedNextSteps} />
                    </div>
                    {agent.approvalsAwaitingUser.length > 0 && (
                      <div className="mt-3 rounded-md bg-white p-3">
                        <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">Awaiting approval</p>
                        <p className="mt-1 text-sm text-stone-700">{agent.approvalsAwaitingUser[0]}</p>
                      </div>
                    )}
                  </article>
                ))}
              </CardContent>
            </Card>

            <div className="grid gap-5 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5" />
                    <h2 className="text-lg font-semibold">Recent Knowledge</h2>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {home.recentKnowledge.map((item) => (
                    <article key={item.id} className="rounded-md bg-surface p-3">
                      <div className="flex items-start justify-between gap-3">
                        <h3 className="text-sm font-semibold">{item.title}</h3>
                        <span className="rounded-full bg-white px-2.5 py-1 text-xs capitalize text-stone-600">{item.kind}</span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.summary}</p>
                    </article>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <Lightbulb className="h-5 w-5" />
                    <h2 className="text-lg font-semibold">Opportunities</h2>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {home.opportunities.map((item) => (
                    <article key={item.id} className="rounded-md bg-surface p-3">
                      <h3 className="text-sm font-semibold">{item.title}</h3>
                      <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.suggestedAction}</p>
                      <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div className="rounded-md bg-white p-2">Impact <span className="font-semibold">{item.expectedImpact}</span></div>
                        <div className="rounded-md bg-white p-2">Confidence <span className="font-semibold">{item.confidence}</span></div>
                      </div>
                    </article>
                  ))}
                </CardContent>
              </Card>
            </div>
          </main>

          <aside className="space-y-5">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <ShieldCheck className="h-5 w-5" />
                  <h2 className="text-lg font-semibold">Pending Approvals</h2>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {home.pendingApprovals.map((approval) => (
                  <article key={approval.id} className="rounded-md border border-border bg-surface p-3">
                    <h3 className="text-sm font-semibold">{approval.title}</h3>
                    <p className="mt-1 text-xs text-muted-foreground">Requested by {approval.requestedBy} / {approval.riskLevel} risk</p>
                    <p className="mt-2 text-sm leading-6 text-stone-700">{approval.preview}</p>
                  </article>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Clock3 className="h-5 w-5" />
                  <h2 className="text-lg font-semibold">Open Loops</h2>
                </div>
              </CardHeader>
              <CardContent className="space-y-2">
                {home.openLoops.map((loop) => (
                  <div key={loop.id} className="rounded-md bg-surface p-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-semibold">{loop.title}</p>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-stone-600">{loop.urgency}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{loop.owner} / {loop.dueLabel}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5" />
                  <h2 className="text-lg font-semibold">Daily Brief</h2>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm font-semibold leading-6">{home.dailyBrief.headline}</p>
                <MiniList title="What changed" items={home.dailyBrief.whatChanged} className="mt-4" />
                <MiniList title="Reminders" items={home.dailyBrief.reminders} className="mt-4" />
                <div className="mt-4 rounded-md bg-stone-900 p-3 text-sm leading-6 text-white">{home.dailyBrief.recommendedNextAction}</div>
              </CardContent>
            </Card>

            <div className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <p className="text-sm font-semibold">Workspace Principles</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {designPrinciples.map((principle) => (
                  <span key={principle} className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-stone-700">{principle}</span>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function MiniList({ title, items, className }: { title: string; items: string[]; className?: string }) {
  return (
    <div className={className}>
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{title}</p>
      <ul className="mt-2 space-y-1.5">
        {items.map((item) => (
          <li key={item} className="text-sm leading-5 text-stone-700">{item}</li>
        ))}
      </ul>
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { Activity, AppWindow, Bell, BookOpen, CheckCircle2, Code2, Database, KeyRound, LockKeyhole, Search, ShieldCheck, SlidersHorizontal, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { synzeptProtocolMock } from "@/lib/synzept-protocol/mock-data";
import type { ProtocolPermissionGrant, ProtocolResourceType } from "@/lib/synzept-protocol/types";

const allFilter = "all";

export function SynzeptProtocolView() {
  const [resourceFilter, setResourceFilter] = useState<ProtocolResourceType | typeof allFilter>(allFilter);
  const [query, setQuery] = useState("");
  const [grants, setGrants] = useState<ProtocolPermissionGrant[]>(synzeptProtocolMock.permissionGrants);

  const visibleResources = useMemo(() => {
    return synzeptProtocolMock.resources.filter((resource) => {
      const matchesType = resourceFilter === allFilter || resource.type === resourceFilter;
      const matchesQuery = `${resource.title} ${resource.summary} ${resource.type}`.toLowerCase().includes(query.toLowerCase());
      return matchesType && matchesQuery;
    });
  }, [query, resourceFilter]);

  const activeGrantCount = grants.filter((grant) => grant.status === "active").length;

  function revokeGrant(id: string) {
    setGrants((current) => current.map((grant) => (grant.id === id ? { ...grant, status: "revoked" } : grant)));
  }

  function requestMockGrant() {
    setGrants((current) => [
      {
        id: `grant-mock-${current.length + 1}`,
        appId: "app-task-bridge",
        appName: "Task Bridge",
        resourceType: "projects",
        scopes: ["read:summary", "write:task_link"],
        status: "pending_user_approval",
        grantedAt: "2026-07-07T19:30:00+05:30",
        expiresAt: null,
        purpose: "Create linked tasks from approved project summaries.",
      },
      ...current,
    ]);
  }

  return (
    <div className="min-h-full bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <header className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="flex items-center gap-2 text-sm font-medium uppercase tracking-[0.18em] text-muted">
                <ShieldCheck className="h-4 w-4" />
                Synzept Protocol {synzeptProtocolMock.version}
              </p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal sm:text-4xl">User-owned context for trusted integrations</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-muted-foreground">
                A mock developer console for resource schemas, scoped grants, subscriptions, audit logs, SDK shape, and approval-based access.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 xl:w-[520px]">
              <Metric label="Resource types" value={synzeptProtocolMock.resourceTypes.length.toString()} />
              <Metric label="Active grants" value={activeGrantCount.toString()} />
              <Metric label="Audit events" value={synzeptProtocolMock.auditLogs.length.toString()} />
            </div>
          </div>
        </header>

        <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
          <main className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="flex items-center gap-2 text-lg font-semibold">
                    <Database className="h-5 w-5" />
                    Resources
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">Initial resource types for profile, work state, decisions, knowledge, and preferences.</p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-white px-3 text-sm">
                    <Search className="h-4 w-4 text-muted" />
                    <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search resources" className="w-full min-w-0 bg-transparent outline-none sm:w-48" />
                  </label>
                  <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-white px-3 text-sm">
                    <SlidersHorizontal className="h-4 w-4 text-muted" />
                    <select value={resourceFilter} onChange={(event) => setResourceFilter(event.target.value as ProtocolResourceType | typeof allFilter)} className="bg-transparent outline-none">
                      <option value={allFilter}>All types</option>
                      {synzeptProtocolMock.resourceTypes.map((type) => <option key={type} value={type}>{type}</option>)}
                    </select>
                  </label>
                </div>
              </div>

              <div className="mt-4 grid gap-3 lg:grid-cols-2">
                {visibleResources.map((resource) => (
                  <article key={resource.id} className="rounded-lg border border-border bg-surface p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{resource.type}</p>
                        <h3 className="mt-1 text-base font-semibold">{resource.title}</h3>
                      </div>
                      <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{resource.version}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-zinc-700">{resource.summary}</p>
                    <div className="mt-3 rounded-md bg-white p-3">
                      <p className="text-xs text-muted-foreground">{resource.schemaUrl}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {Object.entries(resource.data).map(([key, value]) => (
                          <span key={key} className="rounded-full bg-zinc-100 px-2.5 py-1 text-xs text-zinc-700">
                            {key}: {Array.isArray(value) ? value.join(", ") : String(value)}
                          </span>
                        ))}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 className="flex items-center gap-2 text-lg font-semibold">
                    <KeyRound className="h-5 w-5" />
                    Permission Grants
                  </h2>
                  <p className="mt-1 text-sm text-muted-foreground">Every app receives explicit, revocable access to specific resource categories and scopes.</p>
                </div>
                <Button variant="outline" onClick={requestMockGrant}>
                  Request mock grant
                </Button>
              </div>
              <div className="mt-4 space-y-3">
                {grants.map((grant) => (
                  <article key={grant.id} className="rounded-lg border border-border bg-surface p-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-base font-semibold">{grant.appName}</h3>
                          <StatusBadge status={grant.status} />
                        </div>
                        <p className="mt-2 text-sm leading-6 text-zinc-700">{grant.purpose}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <span className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{grant.resourceType}</span>
                          {grant.scopes.map((scope) => <span key={scope} className="rounded-full bg-white px-2.5 py-1 text-xs text-zinc-700">{scope}</span>)}
                        </div>
                      </div>
                      <Button variant="outline" onClick={() => revokeGrant(grant.id)} disabled={grant.status === "revoked"}>
                        Revoke
                      </Button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          </main>

          <aside className="space-y-5">
            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <LockKeyhole className="h-5 w-5" />
                Principles
              </h2>
              <div className="mt-3 space-y-2">
                {synzeptProtocolMock.principles.map((principle) => (
                  <p key={principle} className="rounded-md bg-surface px-3 py-2 text-sm text-zinc-700">{principle}</p>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <Bell className="h-5 w-5" />
                Subscriptions
              </h2>
              <div className="mt-3 space-y-3">
                {synzeptProtocolMock.subscriptions.map((subscription) => (
                  <article key={subscription.id} className="rounded-md bg-surface p-3">
                    <p className="text-sm font-semibold">{subscription.resourceType} changes</p>
                    <p className="mt-1 text-sm leading-6 text-muted-foreground">{subscription.eventTypes.join(", ")} to {subscription.appId}</p>
                    <p className="mt-2 break-all text-xs text-zinc-500">{subscription.callbackUrl}</p>
                  </article>
                ))}
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <BookOpen className="h-5 w-5" />
                Auth Flow
              </h2>
              <p className="mt-2 text-sm font-medium">{synzeptProtocolMock.authFlow.flow}</p>
              <ol className="mt-3 space-y-2 text-sm leading-6 text-zinc-700">
                {synzeptProtocolMock.authFlow.steps.map((step, index) => <li key={step}>{index + 1}. {step}</li>)}
              </ol>
            </section>
          </aside>
        </section>

        <section className="grid gap-5 xl:grid-cols-3">
          <Panel title="SDK Structure" icon={<Code2 className="h-5 w-5" />}>
            <div className="space-y-3">
              {synzeptProtocolMock.sdks.map((sdk) => (
                <article key={sdk.language} className="rounded-md bg-surface p-3">
                  <p className="text-sm font-semibold">{sdk.language}</p>
                  <p className="mt-1 font-mono text-xs text-zinc-600">{sdk.installCommand}</p>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">{sdk.example}</p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Sample Apps" icon={<AppWindow className="h-5 w-5" />}>
            <div className="space-y-3">
              {synzeptProtocolMock.apps.map((app) => (
                <article key={app.id} className="rounded-md bg-surface p-3">
                  <p className="text-sm font-semibold">{app.name}</p>
                  <p className="mt-1 text-sm leading-6 text-muted-foreground">{app.sampleUseCase}</p>
                </article>
              ))}
            </div>
          </Panel>

          <Panel title="Audit Log" icon={<Activity className="h-5 w-5" />}>
            <div className="space-y-3">
              {synzeptProtocolMock.auditLogs.map((event) => (
                <article key={event.id} className="rounded-md bg-surface p-3">
                  <div className="flex items-start gap-2">
                    {event.result === "allowed" ? <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" /> : <XCircle className="mt-0.5 h-4 w-4 text-rose-600" />}
                    <div>
                      <p className="text-sm font-semibold">{event.appName}</p>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">{event.userVisibleSummary}</p>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </Panel>
        </section>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-xs uppercase tracking-[0.12em] text-muted">{label}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: ProtocolPermissionGrant["status"] }) {
  const tone = status === "active" ? "bg-emerald-50 text-emerald-700" : status === "revoked" ? "bg-rose-50 text-rose-700" : "bg-amber-50 text-amber-700";
  return <span className={`rounded-full px-2.5 py-1 text-xs ${tone}`}>{status.replace(/_/g, " ")}</span>;
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        {icon}
        {title}
      </h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

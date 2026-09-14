"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import { useSearchParams } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  TriangleAlert,
  Unplug,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { WorkspacePage } from "@/components/layout/workspace-content";
import { api, type ConnectedApp } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useConnectedAppsStore } from "@/stores/connected-apps";

const services = [
  {
    provider: "google_gmail",
    category: "communication",
    name: "Gmail",
    description: "Gmail helps Synzept understand your communication and follow-ups.",
    logoSrc: "/brands/gmail.svg",
    logoAlt: "Gmail logo",
    overview: "Helps Synzept recognize communication load and follow-up patterns without reading the content of your messages.",
    permissions: "View message metadata and mailbox activity.",
    privacy: "Email bodies, attachments, and drafts stay private. Synzept cannot send mail.",
    searchTerms: "email google inbox messages contacts",
  },
  {
    provider: "microsoft_outlook_mail",
    category: "communication",
    name: "Outlook Mail",
    description: "Outlook helps Synzept understand your communication and follow-ups.",
    logoSrc: "/brands/outlook-mail.svg",
    logoAlt: "Outlook Mail logo",
    overview: "Helps Synzept understand active conversations and waiting-for-reply signals without becoming another inbox.",
    permissions: "Read basic mail metadata, including sender, timestamps, read state, folders, and categories.",
    privacy: "Message bodies, previews, attachments, and drafts stay private. Synzept cannot send mail.",
    searchTerms: "email microsoft office inbox messages",
  },
  {
    provider: "slack",
    category: "communication",
    name: "Slack",
    description: "Slack helps Synzept notice team activity, blockers, and decisions.",
    logoSrc: "/brands/slack.svg",
    logoAlt: "Slack logo",
    overview: "Helps Synzept notice team activity, blockers, and decisions that may need your attention.",
    permissions: "Read workspace, users, joined conversations, mentions, and recent activity.",
    privacy: "Raw message text is not stored. Synzept cannot post, edit, or delete messages, or access channels unavailable to the installed app.",
    searchTerms: "chat collaboration messages team communication",
  },
  {
    provider: "microsoft_teams",
    category: "communication",
    name: "Microsoft Teams",
    description: "Teams helps Synzept notice collaboration, meetings, blockers, and decisions.",
    logoSrc: "/brands/microsoft-teams.svg",
    logoAlt: "Microsoft Teams logo",
    overview: "Helps Synzept understand team activity, discussion momentum, meeting load, blockers, and decisions without becoming another chat client.",
    permissions: "Read joined teams, channels, memberships, mentions, meeting metadata, and recent thread activity.",
    privacy: "Message bodies are processed transiently and never stored. Synzept cannot send messages, edit Teams, create channels, join meetings, or modify conversations.",
    searchTerms: "microsoft teams chat collaboration meetings messages team communication",
  },
  {
    provider: "google_calendar",
    category: "calendar",
    name: "Google Calendar",
    description: "Calendar helps Synzept understand your time and available focus.",
    logoSrc: "/brands/google-calendar.svg",
    logoAlt: "Google Calendar logo",
    overview: "Makes Synzept aware of your schedule so recommendations fit the actual shape of your day.",
    permissions: "View events and availability on your primary calendar.",
    privacy: "Event attachments and other calendars are not accessed. Long-term understanding still requires your approval.",
    searchTerms: "schedule events meetings time availability google",
  },
  {
    provider: "microsoft_outlook_calendar",
    category: "calendar",
    name: "Outlook Calendar",
    description: "Outlook Calendar helps Synzept understand your time and commitments.",
    logoSrc: "/brands/outlook-calendar.svg",
    logoAlt: "Outlook Calendar logo",
    overview: "Helps Synzept account for meetings, conflicts, commitments, and available focus time.",
    permissions: "Read calendar events, attendees, times, recurrence, location, and availability.",
    privacy: "Synzept cannot create, edit, delete, accept, or decline events.",
    searchTerms: "schedule events meetings time availability microsoft office",
  },
  {
    provider: "google_drive",
    category: "files",
    name: "Google Drive",
    description: "Drive helps Synzept understand your projects and recent work.",
    logoSrc: "/brands/google-drive.svg",
    logoAlt: "Google Drive logo",
    overview: "Helps Synzept recognize active projects and where work is moving without opening your files.",
    permissions: "View file names, types, timestamps, owners, and recent activity metadata.",
    privacy: "Document contents are not read or downloaded. Synzept cannot edit files or change sharing.",
    searchTerms: "storage documents files docs sheets google",
  },
  {
    provider: "microsoft_onedrive",
    category: "files",
    name: "OneDrive",
    description: "OneDrive helps Synzept understand your projects and recent work.",
    logoSrc: "/brands/onedrive.svg",
    logoAlt: "OneDrive logo",
    overview: "Helps Synzept understand active documents and project freshness without opening your files.",
    permissions: "Read file names, types, modified timestamps, and lightweight sharing metadata.",
    privacy: "Document contents are not read. Synzept cannot edit, delete, download, or change sharing.",
    searchTerms: "storage documents files microsoft office",
  },
  {
    provider: "google_tasks",
    category: "tasks",
    name: "Google Tasks",
    description: "Google Tasks helps Synzept understand your priorities and open loops.",
    logoSrc: "/brands/google-tasks.svg",
    logoAlt: "Google Tasks logo",
    overview: "Helps Synzept account for active, completed, and delayed work when shaping priorities.",
    permissions: "View task names, lists, due dates, completion status, hierarchy, and timestamps.",
    privacy: "Task notes are not read. Synzept cannot create, edit, delete, reorder, or complete tasks.",
    searchTerms: "todo to do reminders productivity google",
  },
  {
    provider: "microsoft_todo",
    category: "tasks",
    name: "Microsoft To Do",
    description: "Microsoft To Do helps Synzept understand your priorities and open loops.",
    logoSrc: "/brands/microsoft-todo.svg",
    logoAlt: "Microsoft To Do logo",
    overview: "Helps Synzept recognize active, recurring, completed, and overdue work.",
    permissions: "Read task names, lists, status, due dates, importance, recurrence, and timestamps.",
    privacy: "Task bodies are not read. Synzept cannot create, edit, delete, reorder, or complete tasks.",
    searchTerms: "todo to do reminders productivity microsoft office",
  },
  {
    provider: "google_contacts",
    category: "people",
    name: "Google Contacts",
    description: "Google Contacts helps Synzept understand the people in your work.",
    logoSrc: "/brands/google-contacts.svg",
    logoAlt: "Google Contacts logo",
    overview: "Helps Synzept understand who you work with and resolve people naturally in your context.",
    permissions: "View contact names, email addresses, company, job title, and update timestamps.",
    privacy: "Profile photos are not read. Synzept cannot send email, edit, delete, or share contacts.",
    searchTerms: "people address book relationships google",
  },
  {
    provider: "microsoft_people",
    category: "people",
    name: "Microsoft People",
    description: "Microsoft People helps Synzept understand your working relationships.",
    logoSrc: "/brands/microsoft-people.svg",
    logoAlt: "Microsoft People logo",
    overview: "Helps Synzept understand professional relationships and recognize collaborators in your work.",
    permissions: "Read names, email addresses, organizations, job titles, categories, and timestamps.",
    privacy: "Contact photos and notes are not read. Synzept cannot message, edit, delete, or share contacts.",
    searchTerms: "contacts address book relationships microsoft office",
  },
  {
    provider: "github",
    category: "development",
    name: "GitHub",
    description: "GitHub helps Synzept understand engineering progress and review work.",
    logoSrc: "/brands/github.svg",
    logoAlt: "GitHub logo",
    overview: "Helps Synzept understand engineering momentum, review load, releases, and stalled work.",
    permissions: "Read repository metadata, issues, pull requests, commits, reviews, and releases.",
    privacy: "Source file contents are not read. Synzept cannot push, merge, create issues, or modify repositories.",
    searchTerms: "code repositories pull requests engineering developer",
  },
  {
    provider: "notion",
    category: "knowledge",
    name: "Notion",
    description: "Notion helps Synzept understand projects, documentation, and planning.",
    logoSrc: "/brands/notion.svg",
    logoAlt: "Notion logo",
    overview: "Helps Synzept recognize active projects, research, documentation momentum, and stale knowledge from workspace structure and metadata.",
    permissions: "Read selected workspace titles, hierarchy, edit timestamps, and page or database metadata.",
    privacy: "Page content is not stored. Synzept cannot edit, create, delete, archive, restore, or share Notion content.",
    searchTerms: "knowledge notes documentation wiki projects planning research notion",
  },
] as const;

const categories = [
  { id: "calendar", name: "Time intelligence", description: "Understands the shape of your day before recommending how to use it.", unlocks: ["Schedule reasoning", "Focus recommendations", "Conflict detection"] },
  { id: "communication", name: "Communication intelligence", description: "Recognizes communication pressure, follow-ups, and decisions waiting on you.", unlocks: ["Follow-up awareness", "Communication load", "Decision signals"] },
  { id: "files", name: "Project intelligence", description: "Notices where project work is moving without reading document contents.", unlocks: ["Project momentum", "Recent work", "Stalled activity"] },
  { id: "tasks", name: "Priority intelligence", description: "Connects unfinished work and deadlines to what matters now.", unlocks: ["Priority reasoning", "Open-loop detection", "Deadline context"] },
  { id: "people", name: "Relationship intelligence", description: "Understands the people and working relationships around your commitments.", unlocks: ["People context", "Collaboration awareness", "Relationship recall"] },
  { id: "development", name: "Development intelligence", description: "Distinguishes engineering momentum from review and delivery blockers.", unlocks: ["Delivery momentum", "Review blockers", "Release context"] },
  { id: "knowledge", name: "Knowledge intelligence", description: "Recognizes active planning, documentation momentum, and knowledge that may need attention.", unlocks: ["Project context", "Documentation momentum", "Knowledge freshness"] },
] as const;

const starterServices = [
  { provider: "google_calendar", label: "Calendar" },
  { provider: "google_gmail", label: "Gmail" },
  { provider: "slack", label: "Slack" },
] as const;

type Service = (typeof services)[number];
type Provider = Service["provider"];
type BusyAction = "connect" | "sync" | "disconnect";

export default function ConnectedAppsPage() {
  const searchParams = useSearchParams();
  const { apps, refresh, setApp, invalidateContext, isLoading } = useConnectedAppsStore();
  const [busy, setBusy] = useState<{ provider: string; action: BusyAction } | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(() => new Set());
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((force = false) => {
    setError(null);
    return refresh(force).catch(() => {
      setError("Your source status could not load. Nothing has been connected or changed.");
    });
  }, [refresh]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    const calendarResult = searchParams.get("googleCalendar");
    const calendarDetail = searchParams.get("googleCalendarError");
    const workspaceResult = searchParams.get("googleWorkspace");
    const workspaceProvider = searchParams.get("googleService");
    const workspaceDetail = searchParams.get("googleWorkspaceError");
    const microsoftResult = searchParams.get("microsoft365");
    const microsoftProvider = searchParams.get("microsoftService");
    const githubResult = searchParams.get("github");
    const slackResult = searchParams.get("slack");
    const notionResult = searchParams.get("notion");
    const serviceName = labelForProvider(workspaceProvider || "");

    if (calendarResult === "connected") {
      invalidateContext();
      void load(true);
      setNotice("Google Calendar connected.");
    }
    if (calendarResult === "cancelled") setError("Google Calendar connection was cancelled. No calendar data was shared.");
    if (calendarResult === "reconnect") setError("Google Calendar needs one more approval. Reconnect and approve Calendar access.");
    if (calendarResult === "error") {
      const detail = process.env.NODE_ENV !== "production" && calendarDetail ? ` Development detail: ${calendarDetail}` : "";
      setError(`Google Calendar could not be connected. Try again in a moment.${detail}`);
    }
    if (workspaceResult === "connected") {
      invalidateContext();
      void load();
      setNotice(`${serviceName} connected.`);
    }
    if (workspaceResult === "cancelled") setError(`${serviceName} connection was cancelled. No data was shared.`);
    if (workspaceResult === "reconnect") setError(`${serviceName} needs one more approval. Reconnect and approve access.`);
    if (workspaceResult === "error") {
      const detail = process.env.NODE_ENV !== "production" && workspaceDetail ? ` Development detail: ${workspaceDetail}` : "";
      setError(`${serviceName} could not be connected. Try again in a moment.${detail}`);
    }
    if (microsoftResult === "connected") {
      invalidateContext();
      void load();
      setNotice(`${labelForProvider(microsoftProvider || "")} connected.`);
    }
    if (microsoftResult === "cancelled") setError(`${labelForProvider(microsoftProvider || "")} connection was cancelled. No data was shared.`);
    if (microsoftResult === "error") setError(`${labelForProvider(microsoftProvider || "")} could not be connected. Try again in a moment.`);
    if (githubResult === "connected") {
      invalidateContext();
      void load();
      setNotice("GitHub connected.");
    }
    if (githubResult === "cancelled") setError("GitHub connection was cancelled. No repository data was shared.");
    if (githubResult === "error") setError("GitHub could not be connected. Try again in a moment.");
    if (slackResult === "connected") {
      invalidateContext();
      void load();
      setNotice("Slack connected.");
    }
    if (slackResult === "cancelled") setError("Slack connection was cancelled. No workspace data was shared.");
    if (slackResult === "error") setError("Slack could not be connected. Try again in a moment.");
    if (notionResult === "connected") {
      invalidateContext();
      void load();
      setNotice("Notion connected.");
    }
    if (notionResult === "cancelled") setError("Notion connection was cancelled. No workspace data was shared.");
    if (notionResult === "error") setError("Notion could not be connected. Try again in a moment.");
  }, [invalidateContext, load, searchParams]);

  const connect = async (provider: Provider) => {
    setBusy({ provider, action: "connect" });
    setError(null);
    try {
      const { authorizationUrl } = provider === "google_calendar"
        ? await api.connectGoogleCalendar()
        : await api.connectGoogleWorkspaceService(provider);
      window.location.assign(authorizationUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${labelForProvider(provider)} connection could not start.`);
      setBusy(null);
    }
  };

  const sync = async (provider: Provider) => {
    setBusy({ provider, action: "sync" });
    setError(null);
    setNotice(null);
    try {
      const result = provider === "google_calendar"
        ? await api.syncGoogleCalendar()
        : await api.syncGoogleWorkspaceService(provider);
      await load();
      setNotice(`${labelForProvider(provider)} is up to date. ${result.synced} update${result.synced === 1 ? "" : "s"} processed.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : `${labelForProvider(provider)} sync failed.`);
    } finally {
      setBusy(null);
    }
  };

  const disconnect = async (provider: Provider) => {
    if (!window.confirm(`Disconnect ${labelForProvider(provider)}? Synzept will stop learning from this source. Existing understanding remains reviewable.`)) return;
    setBusy({ provider, action: "disconnect" });
    setError(null);
    try {
      const status = provider === "google_calendar"
        ? await api.disconnectGoogleCalendar()
        : await api.disconnectGoogleWorkspaceService(provider);
      setApp(provider, status);
      setNotice(`${labelForProvider(provider)} disconnected.`);
      void api.trackEventOnce("connected_app_disconnected", provider, "connected_apps", { provider });
    } catch (err) {
      void api.trackEventOnce("connected_app_error", provider, "connected_apps", { provider, operation: "disconnect" });
      setError(err instanceof Error ? err.message : `${labelForProvider(provider)} could not be disconnected.`);
    } finally {
      setBusy(null);
    }
  };

  const filteredGroups = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return categories.map((category) => ({
      ...category,
      services: services.filter((service) => {
        if (service.category !== category.id) return false;
        if (!normalizedQuery) return true;
        return `${service.name} ${service.description} ${service.searchTerms} ${category.name} ${category.description} ${category.unlocks.join(" ")}`.toLowerCase().includes(normalizedQuery);
      }),
    })).filter((category) => category.services.length > 0);
  }, [query]);

  const selectedService = services.find((service) => service.provider === selectedProvider) || null;
  const initialLoading = isLoading && Object.keys(apps).length === 0;
  const connectedServices = services.filter((service) => apps[service.provider]?.connected);
  const connectedAreas = categories.filter((category) => connectedServices.some((service) => service.category === category.id));

  return (
    <div className="min-h-full bg-[#faf9f6]">
      <WorkspacePage className="max-w-[960px] pb-24 pt-10 sm:pt-14 lg:pt-16">
        <header className="motion-safe:animate-fade-in">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Connected apps</p>
          <h1 className="mt-4 text-[40px] font-medium leading-[1.08] tracking-[-0.045em] text-stone-950 sm:text-6xl">Connected apps</h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-stone-500 sm:text-[17px]">
            Start with the tools that shape your day so Synzept can understand work, priorities, and routines without adding another layer to manage.
          </p>
        </header>

        <section className="mt-10 grid gap-4 rounded-[28px] border border-stone-200 bg-white/90 p-6 shadow-sm sm:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-accent">Workspace overview</p>
            <h2 className="mt-3 text-2xl font-semibold text-stone-950">Connected sources at a glance</h2>
            <p className="mt-3 text-sm leading-6 text-stone-600">
              Synzept uses your connected services to understand your tasks, calendar, files, and relationships so your workspace feels more useful.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-1">
            <Metric label="Connected sources" value={connectedServices.length} description="Sources currently added to your workspace." />
            <Metric label="Insights enabled" value={connectedAreas.length} description="Areas of intelligence available to Synzept." />
          </div>
        </section>

        <section className="mt-10 border-y border-stone-200/70 py-6" aria-labelledby="workspace-summary-title">
          <div className="grid gap-4 sm:grid-cols-[160px_1fr] sm:items-start sm:gap-8">
            <div>
              <h2 id="workspace-summary-title" className="text-sm font-medium text-stone-900">Your workspace</h2>
              <p className="mt-1 text-sm text-stone-400">
                {initialLoading ? "Checking sources…" : `${connectedServices.length} source${connectedServices.length === 1 ? "" : "s"} connected`}
              </p>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-stone-600">
              {connectedAreas.length ? connectedAreas.map((area) => <span key={area.id}>{area.name}</span>) : <span>Start with Calendar, Gmail, or Slack to get useful context quickly.</span>}
            </div>
          </div>
        </section>

        <button
          type="button"
          onClick={() => setPrivacyOpen(true)}
          className="group mt-6 flex w-full items-start gap-3 py-3 text-left transition duration-200 hover:text-stone-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/25 sm:items-center"
        >
          <ShieldCheck className="mt-0.5 h-[18px] w-[18px] shrink-0 text-accent sm:mt-0" aria-hidden="true" />
          <span className="min-w-0 flex-1 text-sm leading-6 text-stone-600">
            <span className="font-medium text-stone-900">Your data stays under your control.</span>{" "}
            Synzept only accesses the services you choose, and every observation requires approval before becoming long-term understanding.
          </span>
          <span className="hidden shrink-0 items-center gap-1 text-xs font-medium text-stone-500 transition group-hover:text-stone-900 sm:flex">
            Learn more <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
          </span>
        </button>

        <AnimatePresence initial={false} mode="popLayout">
          {notice ? <StatusNotice key="notice" tone="success" message={notice} onDismiss={() => setNotice(null)} /> : null}
          {error ? <StatusNotice key="error" tone="error" message={error} onDismiss={() => setError(null)} /> : null}
        </AnimatePresence>

        {!initialLoading && !connectedServices.length ? (
          <section className="mt-6 rounded-[24px] border border-[#dce5de] bg-white/90 p-5 shadow-sm">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-accent">Good first connections</p>
            <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-stone-950">A few links are enough to make the workspace feel more useful.</h2>
                <p className="mt-2 text-sm leading-6 text-stone-600">Start with the services that influence your day most, then add more as you go.</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {starterServices.map((starter) => (
                  <span key={starter.provider} className="rounded-full border border-stone-200 bg-stone-50 px-3 py-2 text-sm text-stone-600">
                    {starter.label}
                  </span>
                ))}
              </div>
            </div>
          </section>
        ) : null}

        <div className="sticky top-0 z-20 -mx-2 mt-6 bg-[#faf9f6]/90 px-2 py-3 backdrop-blur-xl sm:mt-8">
          <label className="relative block">
            <span className="sr-only">Search sources</span>
            <Search className="pointer-events-none absolute left-4 top-1/2 h-[18px] w-[18px] -translate-y-1/2 text-stone-400" aria-hidden="true" />
            <input
              type="search"
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setCollapsed(new Set());
              }}
              placeholder="Search sources…"
              autoComplete="off"
              className="h-12 w-full appearance-none rounded-xl border border-stone-200/80 bg-white/70 pl-11 pr-11 text-[15px] text-stone-950 outline-none transition placeholder:text-stone-400 focus:border-accent/30 focus:ring-2 focus:ring-accent/10"
            />
            {query ? (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-2 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-xl text-stone-400 transition hover:bg-stone-100 hover:text-stone-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/20"
                aria-label="Clear search"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            ) : null}
          </label>
        </div>

        <div className="mt-4" aria-live="polite" aria-busy={initialLoading}>
          {initialLoading ? (
            <SourceListSkeleton />
          ) : filteredGroups.length ? (
            filteredGroups.map((category) => {
              const isCollapsed = collapsed.has(category.id);
              const connectedCount = category.services.filter((service) => apps[service.provider]?.connected).length;
              return (
                <section key={category.id} className="border-b border-stone-200/70 first:border-t" aria-labelledby={`${category.id}-heading`}>
                  <button
                    type="button"
                    onClick={() => setCollapsed((current) => toggleSetValue(current, category.id))}
                    className="group flex min-h-[68px] w-full items-center gap-3 py-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-accent/20"
                    aria-expanded={!isCollapsed}
                    aria-controls={`${category.id}-sources`}
                  >
                    <ChevronDown className={cn("h-4 w-4 shrink-0 text-stone-400 transition-transform duration-200", isCollapsed && "-rotate-90")} aria-hidden="true" />
                    <h2 id={`${category.id}-heading`} className="flex-1 text-[15px] font-semibold text-stone-900">{category.name}</h2>
                    <span className="text-xs tabular-nums text-stone-400">
                      {connectedCount ? `${connectedCount} ready` : `${category.services.length} available`}
                    </span>
                  </button>

                  <AnimatePresence initial={false}>
                    {!isCollapsed ? (
                      <motion.div
                        id={`${category.id}-sources`}
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
                        className="overflow-hidden"
                      >
                        <div className="pb-3">
                          <div className="mb-3 ml-7 max-w-3xl border-l border-stone-200/80 pl-4">
                            <p className="text-sm leading-6 text-stone-500">{category.description}</p>
                            <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1">
                              {category.unlocks.map((capability) => (
                                <span key={capability} className="text-xs text-stone-400">✓ {capability}</span>
                              ))}
                            </div>
                          </div>
                          {category.services.map((service) => (
                            <SourceRow
                              key={service.provider}
                              service={service}
                              app={apps[service.provider] || null}
                              busy={busy?.provider === service.provider ? busy.action : null}
                              onOpen={() => setSelectedProvider(service.provider)}
                              onConnect={() => void connect(service.provider)}
                            />
                          ))}
                        </div>
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </section>
              );
            })
          ) : (
            <div className="py-20 text-center">
              <p className="text-sm font-medium text-stone-800">No sources found</p>
              <p className="mt-2 text-sm text-stone-500">Try a service or capability such as Calendar, Drive, or Tasks.</p>
              <button type="button" onClick={() => setQuery("")} className="mt-5 text-sm font-medium text-accent hover:text-stone-950">Clear search</button>
            </div>
          )}
        </div>
      </WorkspacePage>

      <AnimatePresence>
        {selectedService ? (
          <SourceDrawer
            service={selectedService}
            app={apps[selectedService.provider] || null}
            busy={busy?.provider === selectedService.provider ? busy.action : null}
            onClose={() => setSelectedProvider(null)}
            onConnect={() => void connect(selectedService.provider)}
            onSync={() => void sync(selectedService.provider)}
            onDisconnect={() => void disconnect(selectedService.provider)}
          />
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {privacyOpen ? <PrivacyDialog onClose={() => setPrivacyOpen(false)} /> : null}
      </AnimatePresence>
    </div>
  );
}

function SourceRow({
  service,
  app,
  busy,
  onOpen,
  onConnect,
}: {
  service: Service;
  app: ConnectedApp | null;
  busy: BusyAction | null;
  onOpen: () => void;
  onConnect: () => void;
}) {
  const status = busy === "connect" ? "connecting" : busy === "sync" ? "syncing" : app?.status || "not_connected";
  const connected = Boolean(app?.connected) && status !== "permission_revoked" && status !== "error";
  const activity = sourceActivity(service, app, status);

  return (
    <div className="group relative flex min-h-[76px] items-center gap-3 px-2 py-2 transition duration-200 hover:bg-white/50 sm:gap-4 sm:px-3">
      <button type="button" onClick={onOpen} className="absolute inset-0 rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/25" aria-label={`View ${service.name} details`} />
      <span className="pointer-events-none grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white/70 sm:h-12 sm:w-12">
        <Image src={service.logoSrc} alt={service.logoAlt} width={32} height={32} className="h-7 w-7 object-contain sm:h-8 sm:w-8" />
      </span>
      <span className="pointer-events-none min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-stone-950 sm:text-[15px]">{service.name}</span>
        <span className="mt-1 block text-xs leading-5 text-stone-500 sm:text-sm">{service.description}</span>
        <span className="mt-1 block text-[11px] text-stone-400 sm:hidden">{labelForStatus(status)}{activity ? ` · ${activity}` : ""}</span>
      </span>
      <span className="pointer-events-none hidden max-w-44 shrink-0 text-right sm:block">
        <span className="block text-xs font-medium text-stone-700">{labelForStatus(status)}</span>
        {activity ? <span className="mt-1 block text-[11px] text-stone-400">{activity}</span> : null}
      </span>
      {!connected ? (
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            onConnect();
          }}
          disabled={Boolean(busy)}
          className="relative z-10 inline-flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-xl bg-stone-900 px-3.5 text-xs font-medium text-white shadow-sm transition hover:-translate-y-px hover:bg-stone-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/25 disabled:pointer-events-none disabled:opacity-45"
        >
          {busy === "connect" ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
          {status === "error" || status === "permission_revoked" ? "Reconnect" : "Connect"}
        </button>
      ) : (
        <ChevronRight className="pointer-events-none h-4 w-4 shrink-0 text-stone-300 transition-transform group-hover:translate-x-0.5 group-hover:text-stone-500" aria-hidden="true" />
      )}
    </div>
  );
}

function SourceDrawer({
  service,
  app,
  busy,
  onClose,
  onConnect,
  onSync,
  onDisconnect,
}: {
  service: Service;
  app: ConnectedApp | null;
  busy: BusyAction | null;
  onClose: () => void;
  onConnect: () => void;
  onSync: () => void;
  onDisconnect: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const closeRef = useRef<HTMLButtonElement>(null);
  const status = busy === "connect" ? "connecting" : busy === "sync" ? "syncing" : app?.status || "not_connected";
  const connected = Boolean(app?.connected) && status !== "permission_revoked" && status !== "error";
  const reconnect = status === "permission_revoked" || status === "error";
  const accountEmail = accountEmailFor(app);

  useDialogBehavior(onClose, closeRef);

  return (
    <motion.div
      className="fixed inset-0 z-[70] flex items-end justify-end bg-stone-950/20 backdrop-blur-[2px] sm:items-stretch"
      initial={reduceMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <motion.aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-drawer-title"
        initial={reduceMotion ? false : { y: "100%", opacity: 0.9 }}
        animate={{ y: 0, x: 0, opacity: 1 }}
        exit={reduceMotion ? undefined : { y: "100%", opacity: 0.9 }}
        transition={{ duration: reduceMotion ? 0 : 0.2, ease: [0.22, 1, 0.36, 1] }}
        className="flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-t-[28px] bg-[#fcfbf8] shadow-[0_-16px_60px_rgba(15,23,42,.13)] sm:h-full sm:max-h-none sm:w-[460px] sm:rounded-none sm:shadow-[-18px_0_60px_rgba(15,23,42,.12)]"
      >
        <div className="mx-auto mt-2.5 h-1 w-10 rounded-full bg-stone-300 sm:hidden" aria-hidden="true" />
        <header className="flex items-start gap-4 border-b border-stone-200/70 px-5 pb-5 pt-5 sm:px-7 sm:pt-7">
          <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-white shadow-sm ring-1 ring-stone-900/[0.05]">
            <Image src={service.logoSrc} alt={service.logoAlt} width={38} height={38} className="h-9 w-9 object-contain" />
          </span>
          <div className="min-w-0 flex-1 pt-0.5">
            <h2 id="source-drawer-title" className="text-xl font-semibold tracking-[-0.02em] text-stone-950">{service.name}</h2>
            <div className="mt-1.5 flex items-center gap-2 text-sm text-stone-500">
              <StatusDot status={status} />
              <span>{labelForStatus(status)}</span>
            </div>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-stone-400 transition hover:bg-stone-100 hover:text-stone-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/20" aria-label="Close details">
            <X className="h-[18px] w-[18px]" aria-hidden="true" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-6 sm:px-7 sm:py-7">
          <DrawerSection title="Overview">
            <p>{service.overview}</p>
          </DrawerSection>

          <dl className="my-6 grid grid-cols-2 gap-3 rounded-2xl bg-stone-100/70 p-4">
            <div>
              <dt className="text-[11px] font-medium uppercase tracking-[0.1em] text-stone-400">Status</dt>
              <dd className="mt-1.5 text-sm font-medium text-stone-800">{labelForStatus(status)}</dd>
            </div>
            <div>
              <dt className="text-[11px] font-medium uppercase tracking-[0.1em] text-stone-400">Last sync</dt>
              <dd className="mt-1.5 text-sm font-medium text-stone-800">{formatDate(app?.lastSyncedAt)}</dd>
            </div>
            {accountEmail ? (
              <div className="col-span-2 border-t border-stone-200/70 pt-3">
                <dt className="text-[11px] font-medium uppercase tracking-[0.1em] text-stone-400">Account</dt>
                <dd className="mt-1.5 truncate text-sm font-medium text-stone-800">{accountEmail}</dd>
              </div>
            ) : null}
          </dl>

          <DrawerSection title="Permissions">
            <p>{app?.privacy?.reads || service.permissions}</p>
          </DrawerSection>

          <div className="my-6 h-px bg-stone-200/70" />

          <DrawerSection title="Privacy" icon={<ShieldCheck className="h-4 w-4 text-accent" />}>
            <p>{app?.privacy?.ignored || service.privacy}</p>
            <p className="mt-2 text-stone-500">New observations require your approval before becoming part of what Synzept understands.</p>
          </DrawerSection>

          {app?.lastErrorMessage ? (
            <p className="mt-6 flex items-start gap-2 rounded-xl bg-amber-50 px-3.5 py-3 text-sm leading-6 text-amber-800" role="alert">
              <TriangleAlert className="mt-1 h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{app.lastErrorMessage}</span>
            </p>
          ) : null}
        </div>

        <footer className="border-t border-stone-200/70 bg-white/70 px-5 py-4 backdrop-blur sm:px-7 sm:py-5">
          {!connected || reconnect ? (
            <Button className="w-full" onClick={onConnect} disabled={Boolean(busy)}>
              {busy === "connect" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {reconnect ? "Reconnect" : `Connect ${service.name}`}
            </Button>
          ) : (
            <div className="flex gap-2.5">
              <Button className="flex-1" onClick={onSync} disabled={Boolean(busy)}>
                {busy === "sync" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RefreshCw className="h-4 w-4" aria-hidden="true" />}
                Sync now
              </Button>
              <Button variant="outline" onClick={onDisconnect} disabled={Boolean(busy)} aria-label={`Disconnect ${service.name}`}>
                {busy === "disconnect" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Unplug className="h-4 w-4" aria-hidden="true" />}
                <span className="hidden sm:inline">Disconnect</span>
              </Button>
            </div>
          )}
        </footer>
      </motion.aside>
    </motion.div>
  );
}

function PrivacyDialog({ onClose }: { onClose: () => void }) {
  const reduceMotion = useReducedMotion();
  const closeRef = useRef<HTMLButtonElement>(null);
  useDialogBehavior(onClose, closeRef);

  return (
    <motion.div
      className="fixed inset-0 z-[80] grid place-items-center bg-stone-950/25 px-4 backdrop-blur-[2px]"
      initial={reduceMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <motion.div
        role="dialog"
        aria-modal="true"
        aria-labelledby="privacy-title"
        initial={reduceMotion ? false : { opacity: 0, y: 12, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={reduceMotion ? undefined : { opacity: 0, y: 8, scale: 0.99 }}
        transition={{ duration: reduceMotion ? 0 : 0.2 }}
        className="w-full max-w-md rounded-[24px] bg-[#fcfbf8] p-6 shadow-[0_24px_80px_rgba(15,23,42,.18)] sm:p-7"
      >
        <div className="flex items-start gap-4">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-emerald-50 text-accent">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="privacy-title" className="text-xl font-semibold tracking-[-0.02em] text-stone-950">You remain in control</h2>
            <p className="mt-2 text-sm leading-6 text-stone-500">Sources are read-only and independently controlled. Connecting one never gives another access.</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-stone-400 hover:bg-stone-100 hover:text-stone-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/20" aria-label="Close privacy information">
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
        <ul className="mt-6 space-y-4">
          {[
            "You choose every source Synzept can access.",
            "You can disconnect a source at any time.",
            "Every observation requires approval before becoming understanding.",
            "Provider access is limited to the permissions shown in its details.",
          ].map((item) => (
            <li key={item} className="flex gap-3 text-sm leading-6 text-stone-600">
              <Check className="mt-1 h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
        <Button className="mt-7 w-full" onClick={onClose}>Got it</Button>
      </motion.div>
    </motion.div>
  );
}

function DrawerSection({ title, icon, children }: { title: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">{icon}{title}</h3>
      <div className="mt-2.5 text-sm leading-6 text-stone-600">{children}</div>
    </section>
  );
}

function StatusDot({ status }: { status: string }) {
  const syncing = status === "connecting" || status === "syncing";
  const attention = status === "error" || status === "permission_revoked";
  return (
    <span
      className={cn(
        "h-1.5 w-1.5 shrink-0 rounded-full bg-stone-300",
        status === "connected" && "bg-emerald-600",
        syncing && "animate-pulse bg-stone-500 motion-reduce:animate-none",
        attention && "bg-amber-500",
      )}
      aria-hidden="true"
    />
  );
}

function StatusNotice({ tone, message, onDismiss }: { tone: "success" | "error"; message: string; onDismiss: () => void }) {
  const Icon = tone === "success" ? CheckCircle2 : TriangleAlert;
  return (
    <motion.div
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      className={cn("mt-4 flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm", tone === "success" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800")}
      role={tone === "success" ? "status" : "alert"}
    >
      <motion.span initial={{ scale: 0.6 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 420, damping: 22 }}>
        <Icon className="h-4 w-4" aria-hidden="true" />
      </motion.span>
      <span className="min-w-0 flex-1">{message}</span>
      <button type="button" onClick={onDismiss} className="grid h-7 w-7 place-items-center rounded-lg opacity-60 hover:bg-black/5 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current" aria-label="Dismiss message">
        <X className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </motion.div>
  );
}

function SourceListSkeleton() {
  return (
    <div className="space-y-1 py-2">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="flex h-[76px] items-center gap-4 px-3">
          <Skeleton className="h-12 w-12 shrink-0 rounded-xl" />
          <div className="min-w-0 flex-1 space-y-2">
            <Skeleton className="h-3.5 w-32" />
            <Skeleton className="h-3 w-56 max-w-full" />
          </div>
          <Skeleton className="h-8 w-20" />
        </div>
      ))}
    </div>
  );
}

function useDialogBehavior(onClose: () => void, focusRef: React.RefObject<HTMLButtonElement | null>) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => focusRef.current?.focus());
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [focusRef, onClose]);
}

function toggleSetValue(current: Set<string>, value: string) {
  const next = new Set(current);
  if (next.has(value)) next.delete(value);
  else next.add(value);
  return next;
}

function labelForStatus(status: string) {
  if (status === "connected") return "Ready";
  if (status === "connecting" || status === "syncing") return "Syncing";
  if (status === "error" || status === "permission_revoked") return "Needs attention";
  return "Available";
}

function sourceActivity(service: Service, app: ConnectedApp | null, status: string) {
  if (status === "connecting") return "Connecting…";
  if (status === "syncing") return "Updating context…";
  if (status === "error" || status === "permission_revoked") return "Reconnect to continue";
  if (!app?.connected) return null;
  if (app.lastSyncedAt) return `Synced ${formatRelativeDate(app.lastSyncedAt)}`;
  const byCategory: Record<Service["category"], string> = {
    calendar: "Providing schedule context",
    communication: "Providing communication context",
    files: "Providing project context",
    tasks: "Providing priority context",
    people: "Providing relationship context",
    development: "Providing delivery context",
    knowledge: "Providing knowledge context",
  };
  return byCategory[service.category];
}

function accountEmailFor(app: ConnectedApp | null) {
  if (!app) return null;
  const account = app as ConnectedApp & { accountEmail?: unknown; connectedAccountEmail?: unknown; email?: unknown };
  const email = account.accountEmail || account.connectedAccountEmail || account.email;
  return typeof email === "string" && email.includes("@") ? email : null;
}

function labelForProvider(provider: string) {
  return services.find((service) => service.provider === provider)?.name || "Source";
}

function Metric({ label, value, description }: { label: string; value: number; description: string }) {
  return (
    <div className="rounded-[20px] border border-stone-200 bg-stone-50 p-4 text-sm text-stone-700">
      <p className="text-xs uppercase tracking-[0.16em] text-stone-400">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-stone-950">{value}</p>
      <p className="mt-2 leading-6 text-stone-600">{description}</p>
    </div>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "Never";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function formatRelativeDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return formatDate(value);
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ArrowUp, CheckCircle2, ChevronDown, ChevronUp, Copy, Download, FileText, List, LoaderCircle, Printer, RotateCcw, Share2, Sparkles, XCircle } from "lucide-react";
import { Markdown } from "@/components/chat/markdown";
import { WorkspacePage } from "@/components/layout/workspace-content";
import { api, type ActionExecution, type Task } from "@/lib/api";
import { buildWorkExecutionNarrative, type WorkItem } from "@/lib/work";

type LiveExecutionStageStatus = "completed" | "active" | "pending" | "failed" | "retrying";
type LiveExecutionStage = { stage: string; status: LiveExecutionStageStatus; timestamp?: string | null; details?: string; icon: string };
type LiveExecutionArtifact = { type: string; title: string; icon: string; status: string; openAction?: string; href?: string | null };
type LiveExecutionConnector = { name: string; status: string; detail: string };
type LiveExecutionVerification = { label: string; status: "passed" | "failed" | "pending"; detail?: string };

function isApprovalPending(status: string | undefined): boolean {
  return status === "waiting_approval" || status === "awaiting_confirmation";
}

type ExecutionExperience = {
  stages: LiveExecutionStage[];
  skillName: string | null;
  connectorStatus: LiveExecutionConnector[];
  artifacts: LiveExecutionArtifact[];
  verification: LiveExecutionVerification[];
  approvalReason: string | null;
  errorReason: string | null;
  finalSummary: {
    goalCompleted: boolean;
    executionTime: string;
    artifactCount: number;
    verificationStatus: string;
    selectedSkill: string;
    connectorsUsed: number;
  };
};

function normalizeConnectorName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("google_calendar") || lower.includes("calendar")) return "Google Calendar";
  if (lower.includes("gmail") || lower.includes("email")) return "Gmail";
  if (lower.includes("google_docs") || lower.includes("docs") || lower.includes("document")) return "Google Docs";
  if (lower.includes("google_sheets") || lower.includes("sheet")) return "Google Sheets";
  if (lower.includes("google_slides") || lower.includes("slides") || lower.includes("presentation")) return "Google Slides";
  if (lower.includes("google_drive") || lower.includes("drive")) return "Google Drive";
  if (lower.includes("browser")) return "Browser";
  if (lower.includes("travel")) return "Travel";
  return name;
}

function normalizeArtifactType(type: string | null | undefined, title?: string): string {
  if (!type && title) {
    const lower = title.toLowerCase();
    if (lower.includes("calendar")) return "Calendar Event";
    if (lower.includes("sheet") || lower.includes("spreadsheet") || lower.includes("table")) return "Spreadsheet";
    if (lower.includes("slide") || lower.includes("presentation") || lower.includes("deck")) return "Presentation";
    if (lower.includes("doc") || lower.includes("document") || lower.includes("proposal") || lower.includes("report")) return "Document";
    if (lower.includes("email") || lower.includes("reply") || lower.includes("draft")) return "Email Draft";
    if (lower.includes("ticket") || lower.includes("itinerary")) return "Ticket";
    if (lower.includes("screenshot") || lower.includes("image")) return "Image";
    if (lower.includes("pdf")) return "PDF";
  }
  if (!type) return "Artifact";
  const lower = type.toLowerCase();
  if (lower.includes("calendar") || lower.includes("event")) return "Calendar Event";
  if (lower.includes("doc") || lower.includes("document")) return "Document";
  if (lower.includes("sheet") || lower.includes("spreadsheet")) return "Spreadsheet";
  if (lower.includes("slide") || lower.includes("presentation")) return "Presentation";
  if (lower.includes("browser")) return "Browser Screenshot";
  if (lower.includes("pdf")) return "PDF";
  if (lower.includes("email") || lower.includes("draft")) return "Email Draft";
  if (lower.includes("ticket") || lower.includes("itinerary")) return "Ticket";
  if (lower.includes("url") || lower.includes("link")) return "URL";
  if (lower.includes("image") || lower.includes("screenshot")) return "Image";
  return "Artifact";
}

function artifactIcon(type: string): string {
  const lower = type.toLowerCase();
  if (lower.includes("calendar")) return "📅";
  if (lower.includes("document")) return "📄";
  if (lower.includes("spreadsheet")) return "📊";
  if (lower.includes("presentation")) return "🎞️";
  if (lower.includes("browser")) return "🌐";
  if (lower.includes("pdf")) return "📄";
  if (lower.includes("email")) return "✉️";
  if (lower.includes("ticket")) return "🎫";
  if (lower.includes("image")) return "🖼️";
  if (lower.includes("url") || lower.includes("link")) return "🔗";
  return "📦";
}

function statusFromText(statusText: string | undefined | null, progress?: number): LiveExecutionStageStatus {
  const normalized = (statusText ?? "").toLowerCase();
  if (normalized.includes("fail") || normalized.includes("error") || normalized.includes("cancel")) return "failed";
  if (normalized.includes("retry")) return "retrying";
  if (normalized.includes("complete") || normalized.includes("success") || progress === 100) return "completed";
  if (normalized.includes("pending") || normalized.includes("waiting") || normalized.includes("approval")) return "pending";
  return "active";
}

function verificationStatusFromText(value: string | undefined | null): "passed" | "failed" | "pending" {
  const normalized = (value ?? "").toLowerCase();
  if (normalized.includes("pass") || normalized.includes("verified") || normalized.includes("success")) return "passed";
  if (normalized.includes("fail") || normalized.includes("error") || normalized.includes("decline")) return "failed";
  return "pending";
}

function normalizeText(value: unknown): string | null {
  return typeof value === "string" && value.trim().length ? value.trim() : null;
}

function normalizeStageLabel(value: string | undefined) {
  if (!value) return "Working";
  return value
    .replace(/_/g, " ")
    .replace(/([A-Z])/g, " $1")
    .replace(/\s+/g, " ")
    .trim();
}

function stageIcon(stage: string) {
  const normalized = stage.toLowerCase();
  if (normalized.includes("understand")) return "🧠";
  if (normalized.includes("plan")) return "🗺️";
  if (normalized.includes("skill")) return "🧩";
  if (normalized.includes("connect")) return "🔌";
  if (normalized.includes("execut")) return "⚙️";
  if (normalized.includes("wait")) return "⏳";
  if (normalized.includes("approval")) return "🛡️";
  if (normalized.includes("verify")) return "✓";
  if (normalized.includes("complete")) return "✅";
  if (normalized.includes("fail")) return "❌";
  if (normalized.includes("retry")) return "🔁";
  return "•";
}

function stageStatusFromAction(status: ActionExecution["status"]): LiveExecutionStageStatus {
  if (status === "completed") return "completed";
  if (status === "failed" || status === "cancelled") return "failed";
  if (isApprovalPending(status)) return "active";
  if (status === "queued") return "pending";
  return "active";
}

function normalizeExecutionStepStatus(rawStatus: string, actionStatus?: ActionExecution["status"]): string {
  if (rawStatus === "waiting_for_approval") {
    if (isApprovalPending(actionStatus)) {
      return "waiting_for_approval";
    }
    if (actionStatus === "completed") {
      return "completed";
    }
    return "approved";
  }
  return rawStatus;
}

function normalizeExecutionStepLabel(rawLabel: string, actionStatus?: ActionExecution["status"]): string {
  const normalized = normalizeStageLabel(rawLabel);
  if (rawLabel === "waiting_for_approval" || normalized.toLowerCase().includes("approval")) {
    if (isApprovalPending(actionStatus)) {
      return normalized;
    }
    return "Approval confirmed";
  }
  return normalized;
}

function buildExecutionExperience(action: ActionExecution | null): ExecutionExperience {
  const metadata = (action?.metadata ?? {}) as Record<string, unknown>;
  const executionPlan = (metadata.execution_plan as Record<string, unknown> | undefined) ?? {};
  const workerResult = (metadata.worker_result as Record<string, unknown> | undefined) ?? {};
  const progressEvents = Array.isArray(metadata.progress_events)
    ? (metadata.progress_events as Array<Record<string, unknown>>)
    : [];
  const logs = Array.isArray(metadata.logs)
    ? (metadata.logs as Array<Record<string, unknown>>)
    : [];
  const connectors = Array.isArray(metadata.required_connectors)
    ? (metadata.required_connectors as unknown[]).map((entry) => normalizeText(entry)).filter(Boolean) as string[]
    : [];
  const connectorStatusEntries = Array.isArray(metadata.connector_statuses)
    ? (metadata.connector_statuses as Array<Record<string, unknown>>) : [];

  const skillName = normalizeText(metadata.selected_skill ?? metadata.skill_name ?? executionPlan.selected_skill ?? workerResult.worker_name ?? workerResult.skill_name) ?? "Workflow Skill";
  const selectedSkill = normalizeText(metadata.selected_skill ?? executionPlan.selected_skill ?? workerResult.worker_name ?? workerResult.skill_name) ?? skillName;
  const connectorStatus: LiveExecutionConnector[] = connectorStatusEntries.length
    ? connectorStatusEntries.map((entry) => ({
        name: normalizeConnectorName(normalizeText(entry.name) ?? normalizeText(entry.connector) ?? "Connector"),
        status: normalizeText(entry.status) ?? normalizeText(entry.state) ?? "Connected",
        detail: normalizeText(entry.detail) ?? normalizeText(entry.message) ?? "In progress",
      }))
    : connectors.length
      ? connectors.map((name) => ({
          name: normalizeConnectorName(name),
          status: action?.status === "completed" ? "Verified" : action?.status === "failed" ? "Failed" : isApprovalPending(action?.status) ? "Awaiting approval" : "Connected",
          detail: action?.status === "completed" ? "Available for verification" : "Execution in progress",
        }))
      : [{
          name: normalizeConnectorName(action?.action_type ?? "Execution"),
          status: action?.status === "completed" ? "Verified" : action?.status === "failed" ? "Failed" : isApprovalPending(action?.status) ? "Awaiting approval" : "Running",
          detail: action?.status === "completed" ? "Execution completed" : "Execution in progress",
        }];

  function normalizeArtifactEntries(value: unknown): Array<Record<string, unknown>> {
    if (Array.isArray(value)) {
      return value.map((item) => (typeof item === "object" && item !== null ? (item as Record<string, unknown>) : { name: String(item), content: String(item) }));
    }
    if (typeof value === "object" && value !== null) {
      return Object.entries(value).map(([key, item]) => {
        if (typeof item === "object" && item !== null) {
          return { name: key, ...(item as Record<string, unknown>) };
        }
        return { name: key, content: item };
      });
    }
    return [];
  }

  function buildStages(): LiveExecutionStage[] {
    if (progressEvents.length) {
      return progressEvents.map((entry) => {
        const stageLabel = normalizeStageLabel(
          normalizeText(entry.label) ?? normalizeText(entry.stage_label) ?? normalizeText(entry.stage_id) ?? normalizeText(entry.stage) ?? "Working"
        );
        const status = statusFromText(
          normalizeText(entry.status) ?? normalizeText(entry.state) ?? undefined,
          typeof entry.progress === "number" ? entry.progress : undefined
        );
        return {
          stage: stageLabel,
          status,
          timestamp: normalizeText(entry.timestamp) ?? normalizeText(entry.updated_at) ?? normalizeText(entry.created_at) ?? action?.updated_at,
          details: normalizeText(entry.details) ?? normalizeText(entry.message) ?? normalizeText(entry.detail) ?? undefined,
          icon: stageIcon(stageLabel),
        };
      });
    }

    const progressSteps = Array.isArray(metadata.progress)
      ? (metadata.progress as unknown[]).filter((entry): entry is string => typeof entry === "string")
      : [];
    if (progressSteps.length) {
      return progressSteps.map((step, index) => {
        const stageLabel = normalizeExecutionStepLabel(step, action?.status);
        const isLast = index === progressSteps.length - 1;
        let status: LiveExecutionStageStatus = "pending";
        if (action?.status === "completed") {
          status = "completed";
        } else if (action?.status === "failed") {
          status = isLast ? "failed" : "completed";
        } else if (isLast) {
          status = "active";
        } else {
          status = "completed";
        }
        return {
          stage: stageLabel,
          status,
          timestamp: action?.updated_at,
          details: undefined,
          icon: stageIcon(stageLabel),
        };
      });
    }

    if (logs.length) {
      return logs.map((entry, index) => {
        const rawStage = normalizeText(entry.label) ?? normalizeText(entry.stage) ?? normalizeText(entry.status) ?? normalizeText(entry.detail) ?? "Working";
        const stageLabel = normalizeExecutionStepLabel(rawStage, action?.status);
        const statusText = normalizeText(entry.status);
        const status = statusText
          ? statusFromText(statusText)
          : index === logs.length - 1
            ? action?.status === "completed" ? "completed" : action?.status === "failed" ? "failed" : "active"
            : "completed";
        return {
          stage: stageLabel,
          status,
          timestamp: normalizeText(entry.timestamp) ?? normalizeText(entry.updated_at) ?? action?.updated_at,
          details: normalizeText(entry.detail) ?? normalizeText(entry.message) ?? undefined,
          icon: stageIcon(stageLabel),
        };
      });
    }

    return [
      {
        stage: normalizeStageLabel(action?.status ?? "Execution"),
        status: stageStatusFromAction(action?.status ?? "queued"),
        timestamp: action?.updated_at,
        details: normalizeText(action?.error) ?? normalizeText(action?.output) ?? undefined,
        icon: stageIcon(normalizeStageLabel(action?.status ?? "Execution")),
      },
    ];
  }

  const stageItems = buildStages();

  const artifactRecord = normalizeArtifactEntries(metadata.artifacts ?? workerResult.artifacts ?? []);
  const requestedArtifacts = artifactRecord.map((entry) => {
    const title = normalizeText(entry.title) ?? normalizeText(entry.name) ?? normalizeText(entry.label) ?? "Artifact";
    const type = normalizeArtifactType(normalizeText(entry.type) ?? normalizeText(entry.artifact_type) ?? undefined, title);
    return {
      type,
      title,
      icon: artifactIcon(type),
      status: normalizeText(entry.status) ?? "Created",
      openAction: normalizeText(entry.url) ?? normalizeText(entry.href) ?? undefined,
      href: normalizeText(entry.url) ?? normalizeText(entry.href) ?? undefined,
    };
  });
  const generatedArtifacts = Array.isArray(workerResult.generated_artifacts) ? workerResult.generated_artifacts as unknown[] : [];
  const generatedArtifactEntries = generatedArtifacts.map((entry) => {
    if (typeof entry === "string") {
      return { type: "Generated", title: entry, icon: artifactIcon("Generated"), status: "Saved", href: null };
    }
    const record = typeof entry === "object" && entry !== null ? (entry as Record<string, unknown>) : { title: String(entry) };
    const title = normalizeText(record.title) ?? normalizeText(record.name) ?? "Generated artifact";
    const type = normalizeArtifactType(normalizeText(record.type) ?? normalizeText(record.artifact_type) ?? undefined, title);
    const href = normalizeText(record.url) ?? normalizeText(record.href) ?? normalizeText(record.path) ?? null;
    return {
      type,
      title,
      icon: artifactIcon(type),
      status: normalizeText(record.status) ?? "Saved",
      href,
    };
  });
  const artifacts = [...requestedArtifacts, ...generatedArtifactEntries].slice(0, 6);

  const verificationSources: Array<Record<string, unknown>> = [];
  const verificationData = metadata.verification as Record<string, unknown> | undefined;
  if (verificationData && Array.isArray(verificationData.checks)) {
    verificationSources.push(...(verificationData.checks as Array<Record<string, unknown>>));
  }
  if (Array.isArray(metadata.verification_results)) {
    (metadata.verification_results as Array<unknown>).forEach((item) => {
      if (typeof item === "object" && item !== null) {
        const entry = item as Record<string, unknown>;
        if (Array.isArray(entry.checks)) {
          verificationSources.push(...(entry.checks as Array<Record<string, unknown>>));
        } else {
          verificationSources.push(entry);
        }
      }
    });
  }
  const workerVerification = workerResult.verification as Record<string, unknown> | undefined;
  if (workerVerification && Array.isArray(workerVerification.checks)) {
    verificationSources.push(...(workerVerification.checks as Array<Record<string, unknown>>));
  }

  const verificationChecks = verificationSources.length
    ? verificationSources.map((check) => ({
        label: normalizeText(check.name) ?? normalizeText(check.label) ?? "Verification",
        status: normalizeText(check.status)?.toLowerCase().includes("fail") ? "failed" : normalizeText(check.status)?.toLowerCase().includes("pass") ? "passed" : "pending",
        detail: normalizeText(check.details) ?? normalizeText(check.reason) ?? undefined,
      }))
    : [];

  const approvalReason = normalizeText(executionPlan.approval_reason) ?? normalizeText(metadata.approval_reason) ?? (action?.status === "waiting_approval" ? "Synzept is ready for your confirmation before the next step can continue." : null);
  const errorReason = normalizeText(action?.error) ?? normalizeText(workerResult.error) ?? null;
  const executionMinutes = action?.created_at && action?.updated_at
    ? Math.max(1, Math.round((Date.parse(action.updated_at) - Date.parse(action.created_at)) / 1000 / 60))
    : 1;

  return {
    stages: stageItems,
    skillName,
    connectorStatus,
    artifacts,
    verification: (verificationChecks.length
      ? verificationChecks
      : [{ label: "Execution accepted", status: action?.status === "completed" ? "passed" : "pending", detail: action?.status === "completed" ? "The result is saved and verified." : "Verification will appear once the system completes its checks." }]) as LiveExecutionVerification[],
    approvalReason,
    errorReason,
    finalSummary: {
      goalCompleted: action?.status === "completed",
      executionTime: `${executionMinutes} min`,
      artifactCount: artifacts.length,
      verificationStatus: action?.status === "completed" ? "Verified" : isApprovalPending(action?.status) ? "Awaiting approval" : action?.status === "failed" ? "Needs follow-up" : "In progress",
      selectedSkill,
      connectorsUsed: connectorStatus.length,
    },
  };
}

export default function ActionExecutionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const actionId = typeof params?.actionId === "string" ? params.actionId : undefined;
  const [action, setAction] = useState<ActionExecution | null>(null);
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [executions, setExecutions] = useState<ActionExecution[]>([]);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [copying, setCopying] = useState<"report" | "section" | null>(null);
  const [activeSection, setActiveSection] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({});
  const [showBackToTop, setShowBackToTop] = useState(false);
  const sectionRefs = useRef<Array<HTMLDivElement | null>>([]);

  const getString = (value: unknown): string => (typeof value === "string" ? value : "");
  const buildSectionId = (title: string, index: number) => title.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || `section-${index + 1}`;

  function parseResearchSections(content: string | null) {
    const normalized = content?.trim();
    if (!normalized) return [] as Array<{ title: string; content: string }>;
    const sections: Array<{ title: string; content: string }> = [];
    let currentTitle = "Report";
    const currentLines: string[] = [];
    const flush = () => {
      const content = currentLines.join("\n").trim();
      if (content || sections.length === 0) {
        sections.push({ title: currentTitle, content });
      }
    };
    for (const line of normalized.split(/\r?\n/)) {
      const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
      if (headingMatch) {
        flush();
        currentTitle = headingMatch[2].trim();
        currentLines.length = 0;
        continue;
      }
      currentLines.push(line);
    }
    flush();
    return sections.filter((section) => section.content.trim().length > 0);
  };

  const extractWorkIdentifiers = (id: string | undefined) => {
    if (!id) return { taskId: null as string | null, executionId: null as string | null, rawId: null as string | null };
    if (id.startsWith("task-")) return { taskId: id.slice(5), executionId: null, rawId: null };
    if (id.startsWith("execution-")) return { taskId: null, executionId: id.slice(10), rawId: null };
    return { taskId: null, executionId: null, rawId: id };
  };

  const fetchAction = useCallback(async () => {
    if (!actionId) return;
    setError(null);
    try {
      const executions = await api.listActionExecutions();
      const { taskId, executionId, rawId } = extractWorkIdentifiers(actionId);
      const executionKey = executionId ?? rawId;

      setExecutions(executions);
      if (executionKey) {
        const matchedExecution = executions.find((item) => item.id === executionKey);
        if (matchedExecution) {
          setAction(matchedExecution);
          setTask(null);
          return;
        }
        if (rawId) {
          const fetchedExecution = await api.getActionExecution(rawId).catch(() => null);
          if (fetchedExecution) {
            setAction(fetchedExecution);
            setTask(null);
            return;
          }
        }
      }

      if (taskId) {
        const tasks = await api.listTasks();
        const matchedTask = tasks.find((item) => item.id === taskId) ?? null;
        if (!matchedTask) {
          throw new Error("Work item not found.");
        }
        const linkedExecution = executions.find((item) => getString(item.metadata?.task_id) === taskId) ?? null;
        setTask(matchedTask);
        setAction(linkedExecution);
        return;
      }

      throw new Error("Work item not found.");
    } catch (cause) {
      setTask(null);
      setAction(null);
      setError(cause instanceof Error ? cause.message : "Could not load work details.");
    } finally {
      setLoading(false);
    }
  }, [actionId]);

  useEffect(() => {
    if (!actionId) return;
    setLoading(true);
    void fetchAction();
  }, [actionId, fetchAction]);

  useEffect(() => {
    if (!action?.id || ["completed", "failed", "cancelled"].includes(action.status)) return;
    return api.subscribeToActionExecution(action.id, (next) => setAction(next), 3500, (cause) => {
      setError(cause instanceof Error ? cause.message : "Could not refresh work details.");
    });
  }, [action?.id, action?.status]);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      const height = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress(height > 0 ? Math.min(100, Math.max(0, (scrollTop / height) * 100)) : 0);
      setShowBackToTop(scrollTop > 700);
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const reportSections = useMemo(() => parseResearchSections(action?.output ?? null), [action?.output]);

  useEffect(() => {
    if (!reportSections.length) {
      setActiveSection(null);
      setExpandedSections({});
      return;
    }
    const nextExpanded = Object.fromEntries(reportSections.map((section) => [section.title, true]));
    setExpandedSections(nextExpanded);
    setActiveSection(buildSectionId(reportSections[0].title, 0));
  }, [reportSections]);

  useEffect(() => {
    if (!reportSections.length) return;
    const elements = sectionRefs.current.filter((element): element is HTMLDivElement => Boolean(element));
    if (!elements.length) return;

    const observer = new IntersectionObserver((entries) => {
      const visibleEntry = entries.filter((entry) => entry.isIntersecting).sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0];
      if (visibleEntry) {
        setActiveSection(visibleEntry.target.getAttribute("data-section-id"));
      }
    }, { rootMargin: "-28% 0px -52% 0px", threshold: [0.15, 0.35, 0.6] });

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [reportSections]);

  const executionId = action?.id ?? null;

  const retry = async () => {
    if (!executionId) return;
    setBusy(true);
    setError(null);
    try {
      const result = await api.retryActionExecution(executionId);
      setAction(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not retry this action.");
    } finally {
      setBusy(false);
    }
  };

  const cancel = async () => {
    if (!executionId) return;
    setBusy(true);
    try {
      const result = await api.cancelActionExecution(executionId);
      setAction(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not cancel this action.");
    } finally {
      setBusy(false);
    }
  };

  const editRequest = () => {
    if (!action) return;
    localStorage.setItem("synzept_chat_draft", `Rewrite this research request and improve it: ${action.request}`);
    router.push("/chat");
  };

  const metadata = action?.metadata as Record<string, unknown> | undefined;
  const previousResearch = useMemo(() => {
    const contextItems = Array.isArray(metadata?.research_memory_context) ? metadata.research_memory_context.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null) : [];
    const currentText = `${action?.title ?? ""} ${action?.request ?? ""}`.toLowerCase();
    return contextItems.map((item) => ({
      id: typeof item.id === "string" ? item.id : undefined,
      summary: typeof item.summary === "string" ? item.summary : "Prior research context",
      confidence: typeof item.confidence === "number" ? item.confidence : null,
    })).concat(
      executions.filter((entry) => entry.id !== action?.id && entry.action_type === "research" && entry.status === "completed").filter((entry) => {
        const target = `${entry.title} ${entry.request}`.toLowerCase();
        return currentText && target && (currentText.includes(target.slice(0, 24)) || target.includes(currentText.slice(0, 24)) || entry.request.toLowerCase().includes(action?.request?.toLowerCase()?.slice(0, 24) ?? ""));
      }).map((entry) => ({
        id: entry.id,
        summary: entry.title,
        confidence: typeof entry.metadata?.confidence_score === "number" ? entry.metadata.confidence_score as number : null,
      }))
    ).slice(0, 4);
  }, [action?.id, action?.request, action?.title, executions, metadata]);
  const getMetadataString = (key: string) => {
    const value = metadata?.[key];
    return typeof value === "string" ? value : undefined;
  };
  const getMetadataNumber = (key: string) => {
    const value = metadata?.[key];
    return typeof value === "number" ? value : undefined;
  };
  const getMetadataValue = (key: string): string | number | undefined => {
    const value = metadata?.[key];
    return typeof value === "string" || typeof value === "number" ? value : undefined;
  };
  const formatDate = (value?: string | null) => {
    if (!value) return null;
    return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(new Date(value));
  };
  const formatDateTime = (value?: string | null) => {
    if (!value) return null;
    return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const exportMarkdown = () => {
    if (!action?.output) return;
    const filename = `${action.title.replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase() || "research-report"}.md`;
    downloadFile(action.output, filename, "text/markdown;charset=utf-8");
  };

  const exportJson = () => {
    if (!action) return;
    const payload = {
      title: action.title,
      request: action.request,
      output: action.output,
      metadata: action.metadata,
      stages: metadata?.research_stages ?? [],
    };
    const filename = `${action.title.replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase() || "research-report"}.json`;
    downloadFile(JSON.stringify(payload, null, 2), filename, "application/json;charset=utf-8");
  };

  const stages = (metadata?.research_stages as Array<{ id?: string; label?: string; status?: string; progress?: number; updated_at?: string }> | undefined) || [];
  const memoryTopics = Array.isArray(metadata?.research_memory_topics) ? metadata.research_memory_topics.filter((entry): entry is string => typeof entry === "string") : [];
  const confidenceScore = typeof metadata?.research_memory_confidence === "number" ? metadata.research_memory_confidence : undefined;
  const relatedResearchCount = previousResearch.length;
  const lastResearchedDate = action?.updated_at ? formatDate(action.updated_at) : null;
  const sectionItems = useMemo(() => reportSections.map((section, index) => ({
    title: section.title,
    content: section.content,
    id: buildSectionId(section.title, index),
  })), [reportSections]);
  const readingTimeMinutes = useMemo(() => {
    const words = reportSections.reduce((total, section) => total + section.content.trim().split(/\s+/).filter(Boolean).length, 0);
    return Math.max(1, Math.ceil(words / 180));
  }, [reportSections]);
  const model = getMetadataString("ai_model") || getMetadataString("model") || getMetadataString("provider_model") || "Unknown";
  const metadataSummary = [
    { label: "Report type", value: getMetadataString("report_type") || (action?.action_type === "research" ? "Research" : "Execution") },
    { label: "Generated", value: getMetadataString("generated_at") ? new Date(getMetadataString("generated_at")!).toLocaleString() : (action?.created_at ? new Date(action.created_at).toLocaleString() : "—") },
    { label: "Last updated", value: action?.updated_at ? new Date(action.updated_at).toLocaleString() : "—" },
    { label: "Reading time", value: `${readingTimeMinutes} min` },
    { label: "Confidence", value: confidenceScore ? `${Math.round(confidenceScore * 100)}%` : "—" },
    { label: "Sources", value: getMetadataNumber("source_count")?.toString() ?? getMetadataString("source_count") ?? "—" },
    { label: "Findings", value: getMetadataNumber("finding_count")?.toString() ?? getMetadataString("finding_count") ?? "—" },
    { label: "Memory", value: relatedResearchCount > 0 ? "Linked" : "Fresh" },
    { label: "Related reports", value: `${relatedResearchCount}` },
    { label: "Model", value: model },
  ];
  const currentSectionIndex = sectionItems.findIndex((section) => section.id === activeSection);
  const currentSectionLabel = sectionItems[currentSectionIndex]?.title ?? (sectionItems[0]?.title ?? "Overview");
  const linkedExecution = action;
  const liveExecutionExperience = useMemo(() => buildExecutionExperience(action), [action]);
  const statusLabel = action?.status ? action.status.replace(/_/g, " ") : task?.status?.replace(/_/g, " ") ?? "Active";
  const progressValue = action?.progress ?? 40;
  const dueDate = task?.due_at || null;
  const narrativeWorkItem: WorkItem | null = action || task ? {
    id: action?.id ?? task?.id ?? "work",
    title: action?.title ?? task?.title ?? "Work",
    summary: action?.request ?? task?.description ?? "Turning your request into a usable next step.",
    status: action ? (action.status === "waiting_approval" ? "waiting_for_approval" : action.status === "completed" ? "completed" : action.status === "failed" ? "failed" : action.status === "queued" || action.status === "running" ? "working" : "planning") : task ? (task.status === "waiting_approval" ? "waiting_for_approval" : task.status === "completed" || task.status === "done" ? "completed" : task.status === "failed" ? "failed" : task.status === "planning" || task.status === "researching" ? "planning" : "working") : "planning",
    statusLabel,
    progress: progressValue,
    created_at: action?.created_at ?? task?.created_at ?? new Date().toISOString(),
    updated_at: action?.updated_at ?? task?.updated_at ?? new Date().toISOString(),
    project_id: action?.project_id ?? task?.project_id ?? null,
    projectName: null,
    due_at: dueDate,
    approvalRequired: isApprovalPending(action?.status) || task?.status === "waiting_approval",
    approvalReason: action?.metadata?.approval_reason ? String(action.metadata.approval_reason) : null,
    output: action?.output ?? null,
    error: action?.error ?? null,
    detail: action?.request ?? task?.description ?? "",
    timeline: [],
    deliverables: [],
    relatedWork: [],
    actionId: action?.id ?? null,
    taskId: task?.id ?? null,
  } : null;
  const narrative = narrativeWorkItem ? buildWorkExecutionNarrative(narrativeWorkItem) : null;
  const summaryLine = narrative
    ? `${narrative.headline}. ${narrative.activity}`
    : action
      ? `${action.action_type === "research" ? "Researching" : "Working through"} this request. Status: ${statusLabel}. ${isApprovalPending(action.status) ? "Your approval is needed before Synzept continues." : action.status === "completed" ? "The work is ready for review." : "No action required right now."}`
      : task
        ? `${task.title}. Status: ${statusLabel}. ${task.status === "waiting_approval" ? "Your approval is needed before Synzept continues." : task.status === "completed" ? "The work is ready for review." : "No action required right now."}`
        : "This work item is being prepared for you.";
  const priority = (task?.priority || action?.metadata?.priority || "Medium") as string;
  const successCriteria = (action?.metadata?.success_criteria as string | undefined) || task?.description || "A clear outcome is prepared for review.";
  const executionPlan = (action?.metadata as Record<string, unknown> | undefined)?.execution_plan as Record<string, unknown> | undefined;
  const executionStepDetails = Array.isArray(executionPlan?.steps)
    ? (executionPlan.steps as Array<Record<string, unknown>>).map((step) => {
        const rawStatus = typeof step.status === "string" ? step.status : "pending";
        return {
          id: typeof step.id === "string" ? step.id : "",
          title: typeof step.title === "string" ? step.title : "",
          status: normalizeExecutionStepStatus(rawStatus, action?.status),
          expected_output: typeof step.expected_output === "string" ? step.expected_output : "",
        };
      })
    : [];
  const expectedDeliverables = Array.isArray(executionPlan?.expected_deliverables) ? executionPlan.expected_deliverables.filter((entry): entry is string => typeof entry === "string") : [];
  const currentStep = (executionPlan?.current_step as string | undefined) || (executionPlan?.activity as string | undefined) || (action?.metadata?.current_step as string | undefined) || narrative?.headline || action?.title || task?.title || "Synzept is preparing the next step.";
  const doingNow = (executionPlan?.activity as string | undefined) || ((action?.metadata?.doing_now as string | undefined) || narrative?.activity || action?.request || task?.description || "Synzept is turning your request into a concrete plan and next move.");
  const whyItMatters = (executionPlan?.approval_reason as string | undefined) || (executionPlan?.objective as string | undefined) || (action?.metadata?.why_it_matters as string | undefined) || narrative?.why || "This step keeps the work moving toward a complete, usable result.";
  const nextStep = expectedDeliverables.length ? `Expected output: ${expectedDeliverables.join(", ")}` : ((executionPlan?.next_step as string | undefined) || (action?.metadata?.next_step as string | undefined) || narrative?.nextStep || (action?.status === "waiting_approval" ? "Awaiting your approval before continuing." : "Synzept will continue with the next step as soon as the current one is complete."));

  const continueResearch = () => {
    if (!action) return;
    localStorage.setItem("synzept_chat_draft", `Continue this research with fresh context: ${action.request}`);
    router.push("/chat");
  };

  const copyText = async (value: string, kind: "report" | "section") => {
    try {
      setCopying(kind);
      await navigator.clipboard.writeText(value);
      setStatusMessage(kind === "report" ? "The full report is copied and ready to share." : "That section is copied and ready to paste.");
    } catch {
      setStatusMessage("Copying is unavailable in this browser. Use the export buttons instead.");
    } finally {
      setCopying(null);
    }
  };

  const handleShare = async () => {
    if (!action?.output) return;
    if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
      try {
        await navigator.share({ title: action.title, text: action.output });
        setStatusMessage("Report shared.");
        return;
      } catch {
        setStatusMessage("Sharing was cancelled. You can still copy or export the report.");
        return;
      }
    }
    setStatusMessage("Share is available on supported devices. You can also copy or export this report.");
  };

  const printReport = () => window.print();
  const exportSection = (section: { title: string; content: string }) => {
    if (!section.content) return;
    const filename = `${section.title.replace(/[^a-z0-9]+/gi, "-").replace(/^-+|-+$/g, "").toLowerCase() || "section"}.md`;
    downloadFile(section.content, filename, "text/markdown;charset=utf-8");
  };
  const timelineItems = action
    ? [
        { label: "Work created", detail: action.request, timestamp: action.created_at },
        ...(stages.length ? [{ label: "Planning completed", detail: stages[0]?.label ?? "The next step is being handled", timestamp: action.updated_at }] : []),
        ...(isApprovalPending(action.status) ? [{ label: "Approval requested", detail: "Your review is needed", timestamp: action.updated_at }] : []),
        ...(action.status === "completed" ? [{ label: "Work completed", detail: "The outcome is ready for review", timestamp: action.updated_at }] : []),
      ]
    : task
      ? [
          { label: "Work created", detail: task.title, timestamp: task.created_at },
          ...(task.status === "waiting_approval" ? [{ label: "Approval requested", detail: "Your review is needed", timestamp: task.updated_at ?? task.created_at }] : []),
          ...(task.status === "completed" ? [{ label: "Work completed", detail: "The outcome is ready for review", timestamp: task.updated_at ?? task.created_at }] : []),
        ]
      : [];
  const deliverables = Array.isArray((action?.metadata as Record<string, unknown> | undefined)?.deliverables)
    ? ((action?.metadata as Record<string, unknown>).deliverables as Array<Record<string, unknown>>).map((item) => ({
        kind: (item.type as string) || "Document",
        title: (item.title as string) || "Deliverable",
        detail: (item.detail as string) || "Ready to review.",
        url: undefined,
      }))
    : action?.output
      ? [{ kind: "Document", title: action.action_type === "research" ? "Research report" : "Generated output", detail: action.output, url: undefined }]
      : [];
  const contextItems = [
    action?.project_id ? { label: "Project", value: action.project_id } : null,
    task?.project_id ? { label: "Project", value: task.project_id } : null,
    task?.priority ? { label: "Priority", value: task.priority } : null,
    action?.action_type ? { label: "Type", value: action.action_type.replace(/_/g, " ") } : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;
  const workContext = Array.isArray((action?.metadata as Record<string, unknown> | undefined)?.work_context)
    ? ((action?.metadata as Record<string, unknown>).work_context as Array<Record<string, unknown>>)
    : [];
  const relatedContextSections = workContext.map((item) => ({
    title: (item.title as string) || "Context",
    detail: (item.detail as string) || "",
    items: Array.isArray(item.items) ? item.items.filter((entry): entry is Record<string, unknown> => typeof entry === "object" && entry !== null) : [],
    source: (item.source as string) || "context",
  }));

  return (
    <div className="min-h-full bg-[#fbfbfa] text-stone-950">
      <div className="sticky top-0 z-30 h-1 bg-stone-100">
        <div className="h-full rounded-full bg-[#58705f] transition-all" style={{ width: `${scrollProgress}%` }} />
      </div>
      <WorkspacePage className="max-w-[980px] pb-24 pt-10 sm:pt-14">
        {showBackToTop ? (
          <button type="button" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} className="fixed bottom-6 right-6 z-40 inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700 shadow-lg transition hover:-translate-y-0.5 hover:bg-stone-50">
            <ArrowUp className="h-4 w-4" /> Back to top
          </button>
        ) : null}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <Link href="/actions" className="inline-flex items-center gap-2 text-sm font-medium text-stone-600 hover:text-stone-900">
              <ArrowLeft className="h-4 w-4" /> Back to work
            </Link>
            <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-stone-950">Work details</h1>
          </div>
          {action ? (
            <div className="flex flex-wrap gap-3">
              {action.status === "failed" && (
                <>
                  <button type="button" disabled={busy} onClick={retry} className="inline-flex items-center gap-2 rounded-xl bg-emerald-950 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:opacity-60">
                    <RotateCcw className="h-4 w-4" /> Retry
                  </button>
                  <button type="button" disabled={busy} onClick={editRequest} className="inline-flex items-center gap-2 rounded-xl border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700 transition hover:border-stone-300 disabled:opacity-60">
                    Edit request
                  </button>
                </>
              )}
              {action.status !== "completed" && action.status !== "failed" && (
                <button type="button" disabled={busy} onClick={cancel} className="inline-flex items-center gap-2 rounded-xl bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100 disabled:opacity-60">
                  <XCircle className="h-4 w-4" /> Cancel
                </button>
              )}
              {action.status === "completed" && (
                <span className="inline-flex items-center gap-2 rounded-xl bg-emerald-100 px-4 py-2 text-sm font-semibold text-emerald-900">
                  <CheckCircle2 className="h-4 w-4" /> Completed
                </span>
              )}
            </div>
          ) : null}
        </div>

        {statusMessage ? (
          <div className="mt-6 rounded-2xl border border-[#dce5de] bg-[#f7fbf8] px-4 py-3 text-sm text-stone-700">
            {statusMessage}
          </div>
        ) : null}

        {loading ? (
          <div className="mt-10 rounded-3xl border border-[#dce5de] bg-white p-8 shadow-sm">
            <div className="flex items-center gap-3">
              <LoaderCircle className="h-8 w-8 animate-spin text-[#58705f]" />
              <div>
                <p className="text-base font-semibold text-stone-900">Gathering the latest progress…</p>
                <p className="mt-1 text-sm text-stone-600">This updates automatically while the work is still active.</p>
              </div>
            </div>
          </div>
        ) : error ? (
          <div className="mt-10 rounded-3xl border border-red-200 bg-red-50 p-8 text-sm text-red-700">
            <p className="text-base font-semibold">We could not load that Work item yet.</p>
            <p className="mt-2 leading-6">{error}</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button type="button" onClick={() => { setLoading(true); void fetchAction(); }} className="rounded-xl bg-red-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-800">Try again</button>
              <Link href="/actions" className="rounded-xl border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100">Back to work</Link>
            </div>
          </div>
        ) : action ? (
          <div className="mt-10 space-y-8">
            <section className="rounded-[32px] border border-stone-200 bg-white p-8 shadow-sm">
              <div className="rounded-[28px] border border-[#dce5de] bg-[#fbfbfa] p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Summary</p>
                <p className="mt-3 text-lg leading-8 text-stone-700">{summaryLine}</p>
              </div>

              {action?.action_type === "research" ? (
                <div className="mt-6 grid gap-3 lg:grid-cols-4">
                  <div className="rounded-2xl border border-[#dce5de] bg-[#fbfbfa] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Previous research</p>
                    <p className="mt-2 text-lg font-semibold text-stone-950">{relatedResearchCount > 0 ? `${relatedResearchCount} related` : "No prior report"}</p>
                    <p className="mt-1 text-sm text-stone-600">{relatedResearchCount > 0 ? "Synzept found relevant continuity signals." : "This is the first report in this thread."}</p>
                  </div>
                  <div className="rounded-2xl border border-[#dce5de] bg-[#fbfbfa] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Last researched</p>
                    <p className="mt-2 text-lg font-semibold text-stone-950">{lastResearchedDate ?? "Recently created"}</p>
                    <p className="mt-1 text-sm text-stone-600">{lastResearchedDate ? "Surface area for continuity" : "Fresh report ready for review"}</p>
                  </div>
                  <div className="rounded-2xl border border-[#dce5de] bg-[#fbfbfa] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Memory confidence</p>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-stone-200">
                        <div className="h-full rounded-full bg-[#58705f]" style={{ width: `${Math.round((confidenceScore ?? 0.75) * 100)}%` }} />
                      </div>
                      <span className="text-sm font-semibold text-stone-900">{confidenceScore ? `${Math.round(confidenceScore * 100)}%` : "75%"}</span>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-[#dce5de] bg-[#fbfbfa] p-4">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Topics</p>
                    <p className="mt-2 text-sm font-semibold text-stone-900">{memoryTopics.length ? memoryTopics.slice(0, 3).join(" • ") : "Context captured"}</p>
                  </div>
                </div>
              ) : null}

              <div className="mt-8 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
                <div className="space-y-6">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-500">Overview</p>
                    <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-stone-950">{action.title}</h2>
                    <p className="mt-4 text-sm leading-7 text-stone-600">{action.request}</p>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                      <p className="text-[11px] text-stone-400">Status</p>
                      <p className="mt-2 text-sm font-semibold text-stone-900">{statusLabel}</p>
                    </div>
                    <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                      <p className="text-[11px] text-stone-400">Progress</p>
                      <p className="mt-2 text-sm font-semibold text-stone-900">{progressValue}%</p>
                    </div>
                    <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                      <p className="text-[11px] text-stone-400">Priority</p>
                      <p className="mt-2 text-sm font-semibold text-stone-900">{priority}</p>
                    </div>
                    <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                      <p className="text-[11px] text-stone-400">Due date</p>
                      <p className="mt-2 text-sm font-semibold text-stone-900">{dueDate ? formatDate(dueDate) : "No deadline"}</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-500">Outcome</p>
                    <p className="mt-3 text-sm leading-7 text-stone-700">{action.output ? action.output.replace(/\s+/g, " ").slice(0, 240) : "A clear outcome will appear here as Synzept finishes the work."}</p>
                  </div>

                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-stone-500">Success criteria</p>
                    <p className="mt-3 text-sm leading-7 text-stone-700">{successCriteria}</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-sm font-semibold text-stone-900">What Synzept needs from you</p>
                    <p className="mt-3 text-sm leading-7 text-stone-600">{isApprovalPending(action.status) ? "Approval is needed before Synzept can continue to the next step." : narrative?.estimate ?? "No immediate action is required right now."}</p>
                    {action.action_type === "research" ? (
                      <button type="button" onClick={continueResearch} className="mt-4 inline-flex items-center gap-2 rounded-full border border-[#dce5de] bg-white px-3 py-2 text-sm font-semibold text-stone-700 transition hover:border-stone-300">
                        Continue previous research
                      </button>
                    ) : null}
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-sm font-semibold text-stone-900">Timeline</p>
                    <div className="mt-4 space-y-3">
                      {timelineItems.map((item, index) => (
                        <div key={`${item.label}-${index}`} className="flex gap-3">
                          <div className="mt-1 h-2.5 w-2.5 rounded-full bg-[#78907f]" />
                          <div>
                            <p className="text-sm font-medium text-stone-900">{item.label}</p>
                            <p className="text-sm text-stone-600">{item.detail}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section className="rounded-[32px] border border-stone-200 bg-white p-8 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Production execution experience</p>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={exportMarkdown} disabled={!action?.output} className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50 disabled:opacity-50">
                    <Download className="h-4 w-4" /> Download MD
                  </button>
                  <button type="button" onClick={exportJson} disabled={!action} className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700 transition hover:bg-stone-50 disabled:opacity-50">
                    <Download className="h-4 w-4" /> Download JSON
                  </button>
                </div>
              </div>

              <div className="mt-6 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
                <div className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-5">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-[#58705f]" />
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Execution timeline</p>
                  </div>
                  <div className="mt-4 space-y-3">
                    {liveExecutionExperience.stages.map((stage, index) => (
                      <div key={`${stage.stage}-${index}`} className="flex items-start gap-3 rounded-2xl border border-stone-200 bg-white p-3">
                        <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-full bg-stone-100 text-lg">{stage.icon}</div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-stone-900">{stage.stage}</p>
                            <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${stage.status === "completed" ? "bg-emerald-100 text-emerald-700" : stage.status === "active" ? "bg-amber-100 text-amber-700" : stage.status === "failed" ? "bg-red-100 text-red-700" : stage.status === "retrying" ? "bg-sky-100 text-sky-700" : "bg-stone-100 text-stone-500"}`}>{stage.status}</span>
                          </div>
                          {stage.timestamp ? <p className="mt-1 text-xs text-stone-500">{new Date(stage.timestamp).toLocaleString()}</p> : null}
                          {stage.details ? <p className="mt-2 text-sm leading-6 text-stone-600">{stage.details}</p> : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Skill card</p>
                    <div className="mt-3 rounded-2xl bg-white p-4">
                      <p className="text-lg font-semibold text-stone-950">{liveExecutionExperience.skillName}</p>
                      <p className="mt-2 text-sm text-stone-600">Current action: {currentStep}</p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Connector status</p>
                    <div className="mt-3 space-y-2">
                      {liveExecutionExperience.connectorStatus.map((connector) => (
                        <div key={`${connector.name}-${connector.status}`} className="rounded-2xl border border-stone-200 bg-white p-3">
                          <div className="flex items-center justify-between gap-3">
                            <p className="text-sm font-semibold text-stone-900">{connector.name}</p>
                            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">{connector.status}</span>
                          </div>
                          <p className="mt-2 text-sm text-stone-600">{connector.detail}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-4 xl:grid-cols-[1fr_0.95fr]">
                <div className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-5">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Artifacts</p>
                  <div className="mt-4 space-y-3">
                    {liveExecutionExperience.artifacts.length ? liveExecutionExperience.artifacts.map((artifact) => (
                      <div key={`${artifact.title}-${artifact.type}`} className="flex items-start gap-3 rounded-2xl border border-stone-200 bg-white p-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-stone-100 text-lg">{artifact.icon}</div>
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-stone-900">{artifact.title}</p>
                            <span className="rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">{artifact.status}</span>
                          </div>
                          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-stone-500">{artifact.type}</p>
                          {artifact.href ? <a href={artifact.href} target="_blank" rel="noreferrer" className="mt-2 inline-flex text-sm font-semibold text-[#58705f]">Open</a> : null}
                        </div>
                      </div>
                    )) : <p className="text-sm text-stone-600">Artifacts will appear immediately as soon as Synzept creates them.</p>}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Verification</p>
                    <div className="mt-3 space-y-2">
                      {liveExecutionExperience.verification.map((item) => (
                        <div key={`${item.label}-${item.status}`} className="rounded-2xl border border-stone-200 bg-white p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-stone-900">{item.label}</p>
                            <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${item.status === "passed" ? "bg-emerald-100 text-emerald-700" : item.status === "failed" ? "bg-red-100 text-red-700" : "bg-stone-100 text-stone-500"}`}>{item.status}</span>
                          </div>
                          {item.detail ? <p className="mt-2 text-sm text-stone-600">{item.detail}</p> : null}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-stone-500">Final summary</p>
                    <div className="mt-3 space-y-2 text-sm text-stone-700">
                      <p><span className="font-semibold text-stone-950">Goal completed:</span> {liveExecutionExperience.finalSummary.goalCompleted ? "Yes" : "In progress"}</p>
                      <p><span className="font-semibold text-stone-950">Execution time:</span> {liveExecutionExperience.finalSummary.executionTime}</p>
                      <p><span className="font-semibold text-stone-950">Artifacts created:</span> {liveExecutionExperience.finalSummary.artifactCount}</p>
                      <p><span className="font-semibold text-stone-950">Verification status:</span> {liveExecutionExperience.finalSummary.verificationStatus}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_0.9fr]">
                <div className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-5">
                  <p className="text-sm font-semibold text-stone-900">Current step</p>
                  <p className="mt-3 text-lg font-medium text-stone-900">{currentStep}</p>
                  <p className="mt-3 text-sm leading-7 text-stone-600">{doingNow}</p>
                </div>
                <div className="space-y-4">
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-sm font-semibold text-stone-900">Why this matters</p>
                    <p className="mt-3 text-sm leading-7 text-stone-600">{whyItMatters}</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                    <p className="text-sm font-semibold text-stone-900">Next planned step</p>
                    <p className="mt-3 text-sm leading-7 text-stone-600">{nextStep}</p>
                  </div>
                </div>
              </div>
            </section>

            {executionStepDetails.length ? (
              <section className="rounded-[32px] border border-stone-200 bg-white p-8 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Execution plan</p>
                <div className="mt-6 space-y-4">
                  {executionStepDetails.map((step) => (
                    <div key={step.id || step.title} className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-stone-900">{step.title || "Step"}</p>
                          {step.expected_output ? <p className="mt-1 text-sm text-stone-600">Expected: {step.expected_output}</p> : null}
                        </div>
                        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${step.status === "completed" ? "bg-emerald-100 text-emerald-700" : step.status === "approved" ? "bg-emerald-100 text-emerald-700" : step.status === "running" ? "bg-amber-100 text-amber-700" : step.status === "waiting_for_approval" ? "bg-amber-100 text-amber-700" : step.status === "failed" ? "bg-red-100 text-red-700" : "bg-stone-100 text-stone-500"}`}>
                          {step.status === "completed" ? "Complete" : step.status === "approved" ? "Approved" : step.status === "running" ? "Running" : step.status === "waiting_for_approval" ? "Waiting for approval" : step.status === "failed" ? "Failed" : "Queued"}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {stages.length ? (
              <section className="rounded-[32px] border border-stone-200 bg-white p-8 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Research stages</p>
                <div className="mt-6 space-y-4">
                  {stages.map((stage) => (
                    <div key={stage.id ?? stage.label} className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-4">
                        <div>
                          <p className="text-sm font-semibold text-stone-900">{stage.label || "Stage"}</p>
                          {typeof stage.progress === "number" ? <p className="mt-1 text-xs text-stone-500">Progress: {stage.progress}%</p> : null}
                        </div>
                        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase ${stage.status === "completed" ? "bg-emerald-100 text-emerald-700" : stage.status === "running" ? "bg-amber-100 text-amber-700" : stage.status === "failed" ? "bg-red-100 text-red-700" : "bg-stone-100 text-stone-500"}`}>
                          {stage.status === "completed" ? "Complete" : stage.status === "running" ? "Running" : stage.status === "failed" ? "Failed" : "Queued"}
                        </span>
                      </div>
                      {typeof stage.progress === "number" ? (
                        <div className="mt-3 h-2 overflow-hidden rounded-full bg-stone-100">
                          <div className="h-full rounded-full bg-[#78907f]" style={{ width: `${stage.progress}%` }} />
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {isApprovalPending(action.status) ? (
              <section className="rounded-[32px] border border-amber-200 bg-amber-50 p-6 shadow-sm">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-700">Approval needed</p>
                    <h3 className="mt-2 text-xl font-semibold text-stone-950">Synzept is ready to send this email.</h3>
                    <p className="mt-3 max-w-2xl text-sm leading-7 text-stone-700">{liveExecutionExperience.approvalReason ?? "This step affects the direction, quality, or scope of the work. Once you approve it, Synzept will continue automatically."}</p>
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button type="button" onClick={async () => {
                      try {
                        const result = await api.approveActionExecution(action.id);
                        setAction(result);
                        await fetchAction();
                      } catch {
                        // ignore
                      }
                    }} className="rounded-2xl bg-stone-950 px-4 py-2 text-sm font-semibold text-white">Approve</button>
                    <button type="button" onClick={async () => {
                      try {
                        const result = await api.rejectActionExecution(action.id);
                        setAction(result);
                        await fetchAction();
                      } catch {
                        // ignore
                      }
                    }} className="rounded-2xl border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700">Cancel</button>
                    <button type="button" onClick={editRequest} className="rounded-2xl border border-stone-200 bg-white px-4 py-2 text-sm font-semibold text-stone-700">Request changes</button>
                  </div>
                </div>
              </section>
            ) : null}

            {deliverables.length ? (
              <section className="rounded-[32px] border border-stone-200 bg-white p-8 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Deliverables</p>
                <div className="mt-6 space-y-4">
                  {deliverables.map((item) => (
                    <div key={item.title} className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-5">
                      <div className="flex items-center gap-2 text-sm font-semibold text-stone-900">
                        <Sparkles className="h-4 w-4 text-[#78907f]" />
                        {item.title}
                      </div>
                      <p className="mt-3 text-sm leading-7 text-stone-600">{item.detail ? item.detail.replace(/\s+/g, " ").slice(0, 260) : "Ready to review."}</p>
                    </div>
                  ))}
                </div>
              </section>
            ) : null}

            {(contextItems.length || relatedContextSections.length) ? (
              <section className="rounded-[32px] border border-stone-200 bg-white p-8 shadow-sm">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Related Context</p>
                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  {contextItems.map((item) => (
                    <div key={item.label} className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                      <p className="text-[11px] text-stone-400">{item.label}</p>
                      <p className="mt-2 text-sm font-semibold text-stone-900">{item.value}</p>
                    </div>
                  ))}
                </div>
                {relatedContextSections.length ? (
                  <div className="mt-6 space-y-4">
                    {relatedContextSections.map((section) => (
                      <div key={section.title} className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-5">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-stone-900">{section.title}</p>
                          <span className="rounded-full border border-stone-200 bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">{section.source}</span>
                        </div>
                        {section.detail ? <p className="mt-3 text-sm leading-7 text-stone-600">{section.detail}</p> : null}
                        {section.items.length ? (
                          <ul className="mt-4 space-y-2">
                            {section.items.map((item, index) => (
                              <li key={`${section.title}-${index}`} className="rounded-xl border border-stone-200 bg-white p-3 text-sm text-stone-700">
                                <p className="font-medium text-stone-900">{String(item.title ?? "Item")}</p>
                                {item.detail ? <p className="mt-1 text-sm text-stone-600">{String(item.detail)}</p> : null}
                              </li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                    ))}
                  </div>
                ) : null}
              </section>
            ) : null}

            {action.output ? (
              <section className="rounded-[32px] border border-stone-200 bg-white p-8 shadow-sm">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Output</p>
                    <h3 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-stone-950">What Synzept produced</h3>
                    <p className="mt-2 text-sm text-stone-600">{currentSectionLabel ? `Currently viewing ${currentSectionLabel}` : "Review the report in a structured, consultant-style reading experience."}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" onClick={() => setExpandedSections((current) => Object.fromEntries(Object.keys(current).map((key) => [key, true]))) } className="rounded-full border border-stone-200 bg-[#fcfdfc] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-stone-600">Expand all</button>
                    <button type="button" onClick={() => setExpandedSections((current) => Object.fromEntries(Object.keys(current).map((key) => [key, false]))) } className="rounded-full border border-stone-200 bg-[#fcfdfc] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-stone-600">Collapse all</button>
                  </div>
                </div>
                <div className="mt-6 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
                  <div className="space-y-4">
                    {sectionItems.length ? (
                      <div className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-4">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-semibold text-stone-900">Contents</p>
                          <span className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">{sectionItems.length} sections</span>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {sectionItems.map((section, index) => {
                            const isActive = activeSection === section.id;
                            return (
                              <button key={section.id} type="button" onClick={() => {
                                const target = sectionRefs.current[index];
                                target?.scrollIntoView({ behavior: "smooth", block: "start" });
                                setActiveSection(section.id);
                              }} className={`rounded-full px-3 py-1.5 text-sm font-medium transition ${isActive ? "bg-[#58705f] text-white" : "bg-white text-stone-700 hover:bg-stone-50"}`}>
                                {section.title}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    ) : null}
                    {reportSections.length ? (
                      sectionItems.map((section, index) => {
                        const isExpanded = expandedSections[section.title] ?? true;
                        return (
                          <article key={section.id} data-section-id={section.id} ref={(node) => { sectionRefs.current[index] = node as HTMLDivElement | null; }} className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-5">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-stone-500">Section {index + 1}</p>
                                <h4 className="mt-2 text-lg font-semibold text-stone-900">{section.title}</h4>
                              </div>
                              <button type="button" onClick={() => setExpandedSections((current) => ({ ...current, [section.title]: !isExpanded }))} className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-sm font-medium text-stone-700">
                                {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                              </button>
                            </div>
                            {isExpanded ? (
                              <div className="mt-4 text-sm leading-8 text-stone-700">
                                <Markdown content={section.content} className="prose-stone" />
                              </div>
                            ) : <p className="mt-4 text-sm text-stone-500">Section collapsed. Reopen to review the details.</p>}
                          </article>
                        );
                      })
                    ) : (
                      <article className="rounded-2xl border border-stone-200 bg-[#fbfbfa] p-5">
                        <Markdown content={action.output} className="prose-stone" />
                      </article>
                    )}
                  </div>

                  <div className="space-y-4">
                    <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                      <p className="text-sm font-semibold text-stone-900">Report metadata</p>
                      <div className="mt-4 space-y-3 text-sm text-stone-600">
                        {metadataSummary.map((item) => (
                          <div key={item.label} className="flex items-start justify-between gap-4">
                            <span>{item.label}</span>
                            <span className="text-right font-medium text-stone-900">{item.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                      <p className="text-sm font-semibold text-stone-900">Report actions</p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        <button type="button" onClick={exportMarkdown} className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700"> <Download className="h-4 w-4" /> Export MD</button>
                        <button type="button" onClick={exportJson} className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700"> <Download className="h-4 w-4" /> Export JSON</button>
                        <button type="button" onClick={handleShare} className="inline-flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-2 text-sm font-semibold text-stone-700"> <Share2 className="h-4 w-4" /> Share</button>
                      </div>
                    </div>
                    {typeof getMetadataValue("tool_summary") === "string" ? (
                      <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                        <p className="text-sm font-semibold text-stone-900">Execution context</p>
                        <p className="mt-3 text-sm leading-7 text-stone-600">{getMetadataValue("tool_summary")}</p>
                      </div>
                    ) : null}
                  </div>
                </div>
              </section>
            ) : null}

            {action.error || liveExecutionExperience.errorReason ? (
              <div className="mt-8 rounded-3xl border border-red-200 bg-red-50 p-5 text-sm text-red-700">
                <p className="font-semibold">Error</p>
                <p className="mt-2">{action.error ?? liveExecutionExperience.errorReason}</p>
                {action.status === "failed" ? (
                  <div className="mt-4 flex flex-wrap gap-3">
                    <button type="button" disabled={busy} onClick={retry} className="rounded-2xl bg-red-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-800 disabled:opacity-60">Retry</button>
                    <button type="button" onClick={cancel} className="rounded-2xl border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100">Cancel</button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : task ? (
          <div className="mt-10 space-y-8 rounded-[32px] border border-[#dce5de] bg-white p-8 shadow-sm">
            <section className="rounded-[28px] border border-stone-200 bg-[#fbfbfa] p-6">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Summary</p>
              <p className="mt-3 text-lg leading-8 text-stone-700">{summaryLine}</p>
            </section>
            <section className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
              <div className="space-y-4">
                <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                  <p className="text-[11px] text-stone-400">Work item</p>
                  <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-stone-950">{task.title}</h2>
                  <p className="mt-4 text-sm leading-7 text-stone-600">{task.description ?? "No additional details were provided for this work item."}</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                    <p className="text-[11px] text-stone-400">Status</p>
                    <p className="mt-2 text-sm font-semibold text-stone-900">{statusLabel}</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                    <p className="text-[11px] text-stone-400">Priority</p>
                    <p className="mt-2 text-sm font-semibold text-stone-900">{priority}</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                    <p className="text-[11px] text-stone-400">Due date</p>
                    <p className="mt-2 text-sm font-semibold text-stone-900">{dueDate ? formatDate(dueDate) : "No deadline"}</p>
                  </div>
                  <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-4">
                    <p className="text-[11px] text-stone-400">Created</p>
                    <p className="mt-2 text-sm font-semibold text-stone-900">{formatDateTime(task.created_at) ?? "Not recorded"}</p>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                  <p className="text-sm font-semibold text-stone-900">Current step</p>
                  <p className="mt-3 text-sm leading-7 text-stone-600">{currentStep}</p>
                </div>
                <div className="rounded-2xl border border-stone-200 bg-[#fcfdfc] p-5">
                  <p className="text-sm font-semibold text-stone-900">Next planned step</p>
                  <p className="mt-3 text-sm leading-7 text-stone-600">{nextStep}</p>
                </div>
              </div>
            </section>
            <section className="rounded-[28px] border border-stone-200 bg-[#fcfdfc] p-6">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Timeline</p>
              <div className="mt-6 space-y-3">
                {timelineItems.map((item, index) => (
                  <div key={`${item.label}-${index}`} className="flex gap-3">
                    <div className="mt-1 h-2.5 w-2.5 rounded-full bg-[#78907f]" />
                    <div>
                      <p className="text-sm font-medium text-stone-900">{item.label}</p>
                      <p className="text-sm text-stone-600">{item.detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
            {linkedExecution ? (
              <section className="rounded-[28px] border border-stone-200 bg-[#fbfbfa] p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[#58705f]">Linked execution</p>
                <p className="mt-3 text-sm leading-7 text-stone-700">{linkedExecution.request}</p>
                {linkedExecution.output ? (
                  <div className="mt-4 rounded-2xl border border-stone-200 bg-white p-4 text-sm leading-6 text-stone-700 whitespace-pre-wrap">{linkedExecution.output}</div>
                ) : null}
              </section>
            ) : (
              <div className="rounded-[28px] border border-stone-200 bg-[#fcfdfc] p-6 text-sm text-stone-600">
                <p className="font-semibold text-stone-900">No execution attached</p>
                <p className="mt-2">This work item is stored as a task. If it is later executed by Synzept, the output and progress will appear here.</p>
              </div>
            )}
          </div>
        ) : (
          <div className="mt-10 rounded-3xl border border-stone-200 bg-white p-8 shadow-sm">Work not found.</div>
        )}
      </WorkspacePage>
    </div>
  );
}

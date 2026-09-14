import type { ActionExecution, Project, Task } from "@/lib/api";

export type WorkStatus =
  | "created"
  | "planning"
  | "working"
  | "waiting_for_approval"
  | "completed"
  | "archived"
  | "failed";

export type WorkTimelineEntry = {
  label: string;
  detail?: string;
  timestamp: string;
};

export type WorkDeliverable = {
  title: string;
  type: string;
  detail?: string;
  url?: string;
};

export type WorkItem = {
  id: string;
  title: string;
  summary: string;
  status: WorkStatus;
  statusLabel: string;
  progress: number;
  created_at: string;
  updated_at: string;
  project_id: string | null;
  projectName: string | null;
  due_at: string | null;
  approvalRequired: boolean;
  approvalReason: string | null;
  output: string | null;
  error: string | null;
  detail: string;
  timeline: WorkTimelineEntry[];
  deliverables: WorkDeliverable[];
  relatedWork: Array<{ id: string; title: string }>;
  actionId: string | null;
  taskId: string | null;
};

const statusLabels: Record<WorkStatus, string> = {
  created: "Created",
  planning: "Planning",
  working: "Working",
  waiting_for_approval: "Waiting for approval",
  completed: "Completed",
  archived: "Archived",
  failed: "Needs attention",
};

export function buildWorkExecutionNarrative(item: WorkItem) {
  const title = item.title || "Your work";
  const normalizedTitle = title.toLowerCase();
  const isWaiting = item.status === "waiting_for_approval";
  const isCompleted = item.status === "completed";
  const isFailed = item.status === "failed";
  const isActive = ["created", "planning", "working"].includes(item.status);

  let activity = "Synzept is getting your work moving.";
  let why = "This keeps the next step grounded in the goals and context already in your workspace.";
  let nextStep = "Synzept will continue with the next useful step as soon as the current one is complete.";
  let estimate = "Estimated completion: just a moment";
  let headline = `${title}`;

  if (isCompleted) {
    activity = "Wrapping up the final review and preparing the outcome for you.";
    why = "This guarantees the result is polished and ready to use.";
    nextStep = "Review the finished output and hand it off to the next step.";
    estimate = "Estimated completion: ready now";
    headline = `Finished ${title}`;
  } else if (isFailed) {
    activity = "Checking what stalled and preparing a more reliable pass.";
    why = "This helps recover from the issue without losing momentum.";
    nextStep = "Synzept will retry with a clearer approach if needed.";
    estimate = "Estimated completion: a short retry";
    headline = `Recovering ${title}`;
  } else if (isWaiting) {
    activity = "Waiting for your approval before the next step can proceed.";
    why = "Your decision keeps the work moving in the right direction.";
    nextStep = "Review the current draft or recommendation and confirm the next step.";
    estimate = "Estimated completion: waiting for your review";
    headline = `Reviewing ${title}`;
  } else if (normalizedTitle.includes("research") || normalizedTitle.includes("competitor") || normalizedTitle.includes("market")) {
    activity = "Reading the latest sources and comparing the key signals.";
    why = "This research helps you make a faster, better-informed decision.";
    nextStep = "Next, Synzept will turn the findings into a concise summary and recommendation.";
    estimate = `Estimated completion: ${item.progress > 70 ? "under a minute" : item.progress > 40 ? "a few minutes" : "just a moment"}`;
    headline = `Researching ${title}`;
  } else if (normalizedTitle.includes("meeting") || normalizedTitle.includes("call") || normalizedTitle.includes("brief")) {
    activity = "Gathering the right context and shaping the brief around your priorities.";
    why = "This helps you walk in prepared without having to stitch the notes together yourself.";
    nextStep = "Synzept will organize the agenda, decisions, and follow-ups into a usable brief.";
    estimate = `Estimated completion: ${item.progress > 70 ? "under a minute" : "a few minutes"}`;
    headline = `Preparing ${title}`;
  } else if (normalizedTitle.includes("email") || normalizedTitle.includes("reply") || normalizedTitle.includes("draft")) {
    activity = "Drafting a response that sounds clear and useful.";
    why = "This saves time and keeps the tone aligned with the work you are trying to move forward.";
    nextStep = "Synzept will refine the draft and surface the most useful version for review.";
    estimate = `Estimated completion: ${item.progress > 60 ? "under a minute" : "a couple minutes"}`;
    headline = `Drafting ${title}`;
  } else if (isActive) {
    activity = "Gathering the next piece of context and turning it into a concrete next step.";
    why = "This keeps the work moving without making you chase down all the details yourself.";
    nextStep = "Synzept will continue the execution path and surface the next clear action.";
    estimate = `Estimated completion: ${item.progress > 60 ? "under a minute" : item.progress > 30 ? "a few minutes" : "just a moment"}`;
    headline = `Working on ${title}`;
  }

  return {
    headline,
    activity,
    why,
    nextStep,
    estimate,
    status: item.status,
    progress: item.progress,
  };
}

export function buildWorkItems(tasks: Task[], executions: ActionExecution[], projects: Project[]): WorkItem[] {
  const projectNames = new Map(projects.map((project) => [project.id, project.name]));
  const executionsByTask = new Map<string, ActionExecution>();
  const executionsWithoutTask: ActionExecution[] = [];

  for (const execution of executions) {
    const taskId = getString(execution.metadata?.task_id);
    if (taskId) {
      executionsByTask.set(taskId, execution);
    } else {
      executionsWithoutTask.push(execution);
    }
  }

  const workItems: WorkItem[] = tasks.map((task) => {
    const execution = executionsByTask.get(task.id);
    return buildWorkItem(task, execution, projectNames, tasks, executions);
  });

  for (const execution of executionsWithoutTask) {
    workItems.push(buildWorkItemFromExecution(execution, projectNames, tasks, executions));
  }

  return workItems.sort((left, right) => dateValue(right.updated_at) - dateValue(left.updated_at));
}

function buildWorkItem(task: Task, execution: ActionExecution | undefined, projectNames: Map<string, string>, tasks: Task[], executions: ActionExecution[]): WorkItem {
  const status = deriveStatus(task, execution);
  const progress = execution ? execution.progress : progressFromStatus(status);
  const projectName = task.project_id ? projectNames.get(task.project_id) ?? null : null;
  const summary = buildSummary(task, execution);
  const timeline = buildTimeline(task, execution);
  const deliverables = buildDeliverables(task, execution);
  const relatedWork = findRelatedWork(`task-${task.id}`, task.project_id, tasks, executions);

  return {
    id: `task-${task.id}`,
    title: task.title,
    summary,
    status,
    statusLabel: statusLabels[status],
    progress,
    created_at: task.created_at,
    updated_at: task.updated_at || task.created_at,
    project_id: task.project_id,
    projectName,
    due_at: task.due_at,
    approvalRequired: status === "waiting_for_approval",
    approvalReason: buildApprovalReason(task, execution),
    output: execution?.output ?? null,
    error: execution?.error ?? null,
    detail: buildDetail(task, execution),
    timeline,
    deliverables,
    relatedWork,
    actionId: execution?.id ?? null,
    taskId: task.id,
  };
}

function buildWorkItemFromExecution(execution: ActionExecution, projectNames: Map<string, string>, tasks: Task[], executions: ActionExecution[]): WorkItem {
  const status = deriveStatus(undefined, execution);
  const progress = execution.progress;
  const projectName = execution.project_id ? projectNames.get(execution.project_id) ?? null : null;
  const summary = execution.output ? truncate(execution.output, 120) : execution.request;
  const timeline = buildExecutionTimeline(execution);
  const deliverables = buildDeliverables(undefined, execution);
  const relatedWork = findRelatedWork(`execution-${execution.id}`, execution.project_id, tasks, executions);

  return {
    id: `execution-${execution.id}`,
    title: execution.title,
    summary,
    status,
    statusLabel: statusLabels[status],
    progress,
    created_at: execution.created_at,
    updated_at: execution.updated_at,
    project_id: execution.project_id,
    projectName,
    due_at: null,
    approvalRequired: status === "waiting_for_approval",
    approvalReason: buildApprovalReason(undefined, execution),
    output: execution.output ?? null,
    error: execution.error ?? null,
    detail: buildDetail(undefined, execution),
    timeline,
    deliverables,
    relatedWork,
    actionId: execution.id,
    taskId: null,
  };
}

function deriveStatus(task?: Task, execution?: ActionExecution): WorkStatus {
  if (execution) {
    switch (execution.status) {
      case "awaiting_confirmation":
      case "waiting_approval":
        return "waiting_for_approval";
      case "planning":
        return task ? task.status === "planning" || task.status === "researching" ? "planning" : "working" : "planning";
      case "executing":
      case "queued":
      case "running":
        return task ? task.status === "planning" || task.status === "researching" ? "planning" : "working" : "working";
      case "completed":
        return "completed";
      case "failed":
      case "cancelled":
        return "failed";
      default:
        return "planning";
    }
  }

  if (!task) return "planning";
  switch (task.status) {
    case "todo":
    case "pending":
      return "created";
    case "queued":
    case "understanding":
    case "planning":
      return "planning";
    case "researching":
    case "executing":
    case "in_progress":
      return "working";
    case "waiting_approval":
      return "waiting_for_approval";
    case "completed":
    case "done":
      return "completed";
    case "archived":
      return "archived";
    case "failed":
      return "failed";
    default:
      return "planning";
  }
}

function progressFromStatus(status: WorkStatus): number {
  switch (status) {
    case "created":
      return 10;
    case "planning":
      return 30;
    case "working":
      return 60;
    case "waiting_for_approval":
      return 85;
    case "completed":
    case "archived":
      return 100;
    case "failed":
      return 50;
  }
}

function buildSummary(task?: Task, execution?: ActionExecution): string {
  if (execution?.output) return truncate(execution.output, 120);
  const plan = execution?.metadata?.execution_plan as Record<string, unknown> | undefined;
  const activity = getString(plan?.activity);
  if (activity) return truncate(activity, 120);
  if (task?.description) return truncate(task.description, 120);
  if (execution?.request) return truncate(execution.request, 120);
  return "Synzept is continuing this work.";
}

function buildDetail(task?: Task, execution?: ActionExecution): string {
  if (execution) {
    if (execution.output) return execution.output;
    const plan = execution.metadata?.execution_plan as Record<string, unknown> | undefined;
    const objective = getString(plan?.objective);
    if (objective) return objective;
    return execution.request;
  }

  return task?.description ?? "No extra details available.";
}

function buildTimeline(task?: Task, execution?: ActionExecution): WorkTimelineEntry[] {
  const entries: WorkTimelineEntry[] = [];
  if (task) {
    entries.push({ label: "Work created", detail: task.title, timestamp: task.created_at });
  }
  if (execution) {
    for (const event of buildExecutionLog(execution)) {
      entries.push(event);
    }
  }
  if (task && task.updated_at && task.updated_at !== task.created_at) {
    entries.push({ label: "Last update", detail: `Updated status to ${task.status.replace(/_/g, " ")}`, timestamp: task.updated_at });
  }
  return entries.sort((left, right) => dateValue(left.timestamp) - dateValue(right.timestamp));
}

function buildExecutionTimeline(execution: ActionExecution): WorkTimelineEntry[] {
  const entries = buildExecutionLog(execution);
  if (!entries.length) {
    entries.push({ label: "Work created", detail: execution.request, timestamp: execution.created_at });
  }
  if (execution.updated_at && execution.updated_at !== execution.created_at) {
    entries.push({ label: "Latest update", detail: execution.status.replace(/_/g, " "), timestamp: execution.updated_at });
  }
  return entries.sort((left, right) => dateValue(left.timestamp) - dateValue(right.timestamp));
}

function buildExecutionLog(execution: ActionExecution): WorkTimelineEntry[] {
  const metadata = execution.metadata as Record<string, unknown> | undefined;
  const logs = Array.isArray(metadata?.logs) ? metadata.logs : [];
  const entries: WorkTimelineEntry[] = [];
  for (const log of logs) {
    if (typeof log !== "object" || log === null) continue;
    const status = getString((log as Record<string, unknown>).status);
    const detail = getString((log as Record<string, unknown>).detail);
    entries.push({ label: humanizeStatus(status), detail, timestamp: execution.created_at });
  }
  const plan = metadata?.execution_plan as Record<string, unknown> | undefined;
  const activity = getString(plan?.activity);
  if (activity) {
    entries.push({ label: "Current activity", detail: activity, timestamp: execution.updated_at || execution.created_at });
  }
  const completionSummary = getString(plan?.completion_summary);
  if (completionSummary) {
    entries.push({ label: "Completion summary", detail: truncate(completionSummary, 120), timestamp: execution.updated_at || execution.created_at });
  }
  if (entries.length === 0) {
    entries.push({ label: "Work created", detail: execution.request, timestamp: execution.created_at });
  }
  return dedupeTimeline(entries);
}

function buildDeliverables(task?: Task, execution?: ActionExecution): WorkDeliverable[] {
  const items: WorkDeliverable[] = [];
  if (execution?.output) {
    items.push({ title: execution.action_type ? capitalize(execution.action_type) : "Delivery", type: "Document", detail: truncate(execution.output, 140) });
  }
  const attachments = Array.isArray(execution?.metadata?.attachments) ? execution?.metadata?.attachments : [];
  for (const attachment of attachments) {
    if (typeof attachment === "object" && attachment !== null && typeof (attachment as Record<string, unknown>).filename === "string") {
      items.push({ title: (attachment as Record<string, unknown>).filename as string, type: "File", detail: undefined, url: getString((attachment as Record<string, unknown>).url) });
    }
  }
  return items;
}

function buildApprovalReason(task?: Task, execution?: ActionExecution): string | null {
  if (execution?.status === "waiting_approval") {
    const metadata = execution.metadata as Record<string, unknown> | undefined;
    const plan = getString(metadata?.plan) || getString(metadata?.approval_reason);
    return plan ? `Synzept needs your approval to continue: ${plan}` : "Synzept needs your approval before it can continue this work.";
  }
  if (task?.status === "waiting_approval") {
    return "This work is paused for your approval.";
  }
  return null;
}

function findRelatedWork(currentItemId: string, projectId: string | null | undefined, tasks: Task[], executions: ActionExecution[]) {
  if (!projectId) return [];
  const related: Array<{ id: string; title: string }> = [];
  for (const item of tasks) {
    const itemId = `task-${item.id}`;
    if (item.project_id === projectId && itemId !== currentItemId) {
      related.push({ id: itemId, title: item.title });
    }
  }
  for (const item of executions) {
    const itemId = `execution-${item.id}`;
    if (item.project_id === projectId && itemId !== currentItemId && !getString(item.metadata?.task_id)) {
      related.push({ id: itemId, title: item.title });
    }
  }
  return related.slice(0, 4);
}

function getString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function truncate(value: string, limit: number) {
  if (value.length <= limit) return value;
  return `${value.slice(0, limit - 1).trim()}…`;
}

function capitalize(value: string) {
  if (!value) return value;
  return value[0].toUpperCase() + value.slice(1);
}

function humanizeStatus(status: string): string {
  if (!status) return "Update";
  return status.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function dedupeTimeline(entries: WorkTimelineEntry[]) {
  const seen = new Set<string>();
  return entries.filter((entry) => {
    const key = `${entry.label}:${entry.detail || ""}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function dateValue(value: string) {
  return new Date(value).getTime();
}

export type ExecutionPhase = "idle" | "queued" | "running" | "completed" | "failed" | "waiting_approval" | "cancelled" | (string & {});

type PersistedExecution = { id: string; conversation_id?: string | null; updated_at?: string | null };

export function selectPersistedExecution<T extends PersistedExecution>(executions: T[], conversationId: string | null): T | null {
  if (!conversationId) return executions[0] ?? null;
  return executions
    .filter((execution) => execution.conversation_id === conversationId)
    .sort((left, right) => String(right.updated_at || "").localeCompare(String(left.updated_at || "")))[0] ?? null;
}

export function deriveExecutionProgress(status: ExecutionPhase, steps: Array<string | null | undefined>) {
  if (status === "completed") return 100;
  if (status === "failed") return 35;
  if (status === "waiting_approval") return 60;
  if (status === "cancelled") return 0;
  if (!steps.length) return 18;

  const completedCount = steps.filter((step) => step === "completed").length;
  const activeCount = steps.filter((step) => step === "running").length;
  const total = steps.length;
  const base = Math.round((completedCount / total) * 100);
  const activeOffset = activeCount ? 24 : 0;
  const bounded = Math.min(92, Math.max(12, Math.round(base * 0.72) + activeOffset));
  return bounded;
}

export function getExecutionLiveMessage(status: ExecutionPhase, currentStep: string | null | undefined) {
  if (status === "completed") return "The work is finished and ready for review.";
  if (status === "failed") return "Synzept hit a blocker and is preparing the next best step.";
  if (status === "waiting_approval") return "The plan is ready and waiting for your approval.";
  if (status === "cancelled") return "This run was stopped before it could finish.";
  if (status === "queued") return "Synzept is preparing the best next step for your request.";

  const step = currentStep?.trim() || "Working through the request";
  return `${step} — Synzept is shaping the first draft for you.`;
}

export function getExecutionStatusTone(status: ExecutionPhase) {
  if (status === "completed") return "Complete";
  if (status === "failed") return "Needs a follow-up";
  if (status === "waiting_approval") return "Awaiting approval";
  if (status === "cancelled") return "Stopped";
  if (status === "queued") return "Queued";
  return "In motion";
}

export function getHumanExecutionMessage(step: string | null | undefined) {
  const normalized = (step || "").toLowerCase();
  if (normalized.includes("understand") || normalized.includes("request")) return "Understanding what you need...";
  if (normalized.includes("plan") || normalized.includes("approach")) return "Planning the best approach...";
  if (normalized.includes("research") || normalized.includes("gather") || normalized.includes("info")) return "Gathering relevant information...";
  if (normalized.includes("write") || normalized.includes("draft") || normalized.includes("generate")) return "Writing your document...";
  if (normalized.includes("review") || normalized.includes("quality")) return "Reviewing for quality...";
  if (normalized.includes("save") || normalized.includes("result")) return "Saving your work...";
  return "Preparing it for editing...";
}

export function getUserFacingExecutionError(error: string | null | undefined, request: string | null | undefined) {
  const normalized = (error || "").toLowerCase();
  const requestText = (request || "").toLowerCase();
  if (normalized.includes("permission") || normalized.includes("access") || normalized.includes("calendar")) {
    if (requestText.includes("calendar") || requestText.includes("meeting")) return "I need access to Google Calendar to prepare this brief.";
    return "I couldn't access the information needed for this request. Check the connected app and try again.";
  }
  if (normalized.includes("rate") || normalized.includes("too many") || normalized.includes("temporarily")) return "Synzept is temporarily busy. Please try again in a moment.";
  return "I couldn't complete that request. Please check your connected apps and try again.";
}

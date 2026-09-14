export type AgentPlanStep = {
  id?: string;
  title?: string;
  status?: string;
  description?: string;
};

export type AgentPlanLike = {
  goal?: string;
  description?: string;
  steps?: AgentPlanStep[];
  [key: string]: unknown;
};

const TOOL_PROGRESS_MESSAGES: Record<string, string> = {
  calendar: "Finding your upcoming meetings",
  calendar_list_upcoming_events: "Finding your upcoming meetings",
  "calendar.list_upcoming_events": "Finding your upcoming meetings",
  google_calendar: "Finding your upcoming meetings",
  pdf: "Creating your PDF",
  pdf_generation: "Creating your PDF",
  gmail: "Working with your email",
  gmail_send_email: "Working with your email",
  "gmail.send_email": "Working with your email",
  email: "Working with your email",
  research: "Gathering relevant context",
  browser: "Working through the web context",
};

export function getToolProgressMessage(toolName?: string | null): string {
  if (!toolName) return "Working on your request";
  const normalized = String(toolName).trim().toLowerCase();
  const direct = TOOL_PROGRESS_MESSAGES[normalized] || TOOL_PROGRESS_MESSAGES[normalized.replace(/[^a-z0-9_\.]+/g, "_")];
  if (direct) return direct;
  if (normalized.includes("calendar")) return "Finding your upcoming meetings";
  if (normalized.includes("pdf") || normalized.includes("document")) return "Creating your PDF";
  if (normalized.includes("gmail") || normalized.includes("email")) return "Working with your email";
  return "Working on your request";
}

export function sanitizeAgentPlan(plan: Record<string, unknown> | null | undefined): { goal?: string; description?: string; steps?: AgentPlanStep[] } | null {
  if (!plan || typeof plan !== "object") return null;
  const steps = Array.isArray(plan.steps)
    ? plan.steps
        .filter((step): step is Record<string, unknown> => !!step && typeof step === "object")
        .map((step) => {
          const entry: AgentPlanStep = {};
          if (typeof step.id === "string") entry.id = step.id;
          if (typeof step.title === "string") entry.title = step.title;
          else if (typeof step.description === "string") entry.title = step.description;
          if (typeof step.status === "string") entry.status = step.status;
          if (typeof step.description === "string") entry.description = step.description;
          return entry;
        })
        .filter((step) => step.title || step.id || step.description)
    : [];

  const payload: { goal?: string; description?: string; steps?: AgentPlanStep[] } = {};
  if (typeof plan.goal === "string") payload.goal = plan.goal;
  if (typeof plan.description === "string") payload.description = plan.description;
  if (steps.length) payload.steps = steps;
  return Object.keys(payload).length ? payload : null;
}

import { api, type CalendarContext, type Dashboard, type Goal, type MemoryTrustRecord, type Note, type Project } from "@/lib/api";

export type WorkflowPlan = {
  workflowType: string;
  title: string;
  summary: string;
  prompt: string;
  taskTitle: string;
  taskDescription: string;
  noteTitle: string;
  noteBody: string;
  actionLabel?: string;
};

export type WorkflowExecutionPlan = {
  workflowType: string;
  status: "Preparing" | "Ready" | "Waiting for User" | "Completed" | "Archived";
  nextActionLabel: string;
  nextActionDescription: string;
  progress: number;
  intent?: string;
  currentStep?: string;
  remainingSteps?: string[];
  skills?: string[];
  approvalRequired?: boolean;
};

export async function executeWorkflowFromRequest(request: string): Promise<WorkflowPlan> {
  return executeWorkflowAction("general-planning", request);
}

export async function executeWorkflowAction(actionId: string, request: string): Promise<WorkflowPlan> {
  const plan = buildWorkflowPlan(request, actionId);
  try {
    const [dashboard, goals, projects, notes, calendar, understanding] = await Promise.all([
      api.getDashboard().catch(() => null),
      api.listGoals().catch(() => []),
      api.listProjects().catch(() => []),
      api.listNotes(undefined, request).catch(() => []),
      api.getGoogleCalendarContext().catch(() => null),
      api.relevantUnderstanding(request, undefined, 3).catch(() => []),
    ]);

    const context = buildContextSnapshot({ dashboard, goals, projects, notes, calendar, understanding });
    const noteBody = buildWorkflowContent(plan.workflowType, request, context);
    const taskDescription = buildTaskDescription(plan.workflowType, request, context);

    await Promise.all([
      api.createTask({
        title: plan.taskTitle,
        description: taskDescription,
        priority: "medium",
      }),
      api.createNote({
        title: plan.noteTitle,
        content: noteBody,
      }),
    ]);
  } catch {
    // Keep the workflow moving even if the workspace write fails.
  }
  return plan;
}

export function buildWorkflowExecutionPlan(workflowType: string, request: string, context: Pick<ReturnType<typeof buildContextSnapshot>, "currentProject" | "focus">): WorkflowExecutionPlan {
  const normalized = workflowType.toLowerCase();
  const requestText = request.toLowerCase();

  if (normalized.includes("meeting") || requestText.includes("meeting") || requestText.includes("call")) {
    return {
      workflowType,
      status: "Ready",
      nextActionLabel: "Create action items",
      nextActionDescription: "Turn the meeting brief into the follow-up work that needs to happen next.",
      progress: 70,
      intent: "Meeting preparation",
      currentStep: "Reading the meeting context",
      remainingSteps: ["Draft the agenda", "Extract the decisions", "Prepare the follow-up"],
      skills: ["Calendar Skill", "Writing Skill"],
      approvalRequired: false,
    };
  }

  if (normalized.includes("podcast") || requestText.includes("podcast")) {
    return {
      workflowType,
      status: "Ready",
      nextActionLabel: "Generate episode assets",
      nextActionDescription: "Turn the brief into titles, descriptions, and short-form content for distribution.",
      progress: 75,
      intent: "Content preparation",
      currentStep: "Gathering the source notes",
      remainingSteps: ["Shape the outline", "Draft the assets", "Package the final brief"],
      skills: ["Research Skill", "Writing Skill"],
      approvalRequired: false,
    };
  }

  if (normalized.includes("weekly") || requestText.includes("tomorrow") || requestText.includes("week")) {
    return {
      workflowType,
      status: "Ready",
      nextActionLabel: "Reserve focus blocks",
      nextActionDescription: `Turn the plan into a concrete calendar structure around ${context.currentProject || context.focus || "your next priority"}.`,
      progress: 80,
      intent: "Planning",
      currentStep: "Reviewing your priorities",
      remainingSteps: ["Map the calendar", "Protect focus time", "Capture follow-up work"],
      skills: ["Calendar Skill", "Planning Skill"],
      approvalRequired: false,
    };
  }

  if (normalized.includes("email") || requestText.includes("email") || requestText.includes("reply")) {
    return {
      workflowType,
      status: "Waiting for User",
      nextActionLabel: "Approve the draft",
      nextActionDescription: "Let the user review the reply before it is sent or stored as the next step.",
      progress: 60,
      intent: "Communication",
      currentStep: "Drafting the response",
      remainingSteps: ["Review the draft", "Send or save it"],
      skills: ["Communication Skill"],
      approvalRequired: true,
    };
  }

  if (requestText.includes("train") || requestText.includes("ticket") || requestText.includes("travel")) {
    return {
      workflowType,
      status: "Preparing",
      nextActionLabel: "Collect travel requirements",
      nextActionDescription: "Gather the travel constraints, compare options, and pause for approval before booking.",
      progress: 35,
      intent: "Travel booking",
      currentStep: "Understanding the travel goal",
      remainingSteps: ["Find suitable options", "Compare prices and timing", "Book after approval"],
      skills: ["Travel Skill", "Calendar Skill"],
      approvalRequired: true,
    };
  }

  return {
    workflowType,
    status: "Ready",
    nextActionLabel: "Create the next action",
    nextActionDescription: "Turn the prepared artifact into a concrete next step with context and ownership.",
    progress: 65,
    intent: "Execution planning",
    currentStep: "Preparing the first step",
    remainingSteps: ["Collect context", "Select the best skill", "Deliver the result"],
    skills: ["Planning Skill"],
    approvalRequired: false,
  };
}

function buildWorkflowPlan(request: string, actionId = "default"): WorkflowPlan {
  const normalized = request.toLowerCase();
  const action = actionId.toLowerCase();

  if (normalized.includes("podcast") || action.includes("podcast")) {
    return {
      workflowType: "prepare-podcast",
      title: "Prepare Podcast",
      summary: "Generate a polished prep brief with questions, outline, and follow-up ideas.",
      prompt: `Prepare for the podcast: ${request}`,
      taskTitle: "Prepare podcast brief",
      taskDescription: "Create a structured podcast prep brief with questions, outline, and follow-up items.",
      noteTitle: `Podcast prep • ${shorten(request)}`,
      noteBody: "",
      actionLabel: "Prepare podcast",
    };
  }

  if (normalized.includes("meeting") || normalized.includes("call") || action.includes("meeting")) {
    return {
      workflowType: "prepare-meeting",
      title: "Prepare Meeting",
      summary: "Generate a meeting brief with agenda, risks, decisions, and follow-up actions.",
      prompt: `Prepare for the meeting: ${request}`,
      taskTitle: "Prepare meeting brief",
      taskDescription: "Create a structured meeting brief with agenda, risks, decisions, and follow-up items.",
      noteTitle: `Meeting prep • ${shorten(request)}`,
      noteBody: "",
      actionLabel: "Prepare meeting",
    };
  }

  if (normalized.includes("email") || normalized.includes("reply") || action.includes("email") || action.includes("reply")) {
    return {
      workflowType: "draft-email",
      title: "Draft Email",
      summary: "Create a polished email draft with subject, body, CTA, and follow-up options.",
      prompt: `Draft a thoughtful email for: ${request}`,
      taskTitle: "Draft the email response",
      taskDescription: "Create a polished email draft with subject, body, CTA, and follow-up notes.",
      noteTitle: `Email draft • ${shorten(request)}`,
      noteBody: "",
      actionLabel: "Draft reply",
    };
  }

  if (normalized.includes("week") || normalized.includes("weekly") || normalized.includes("tomorrow") || action.includes("tomorrow") || action.includes("week")) {
    const isReview = /review|weekly review/i.test(request);
    return {
      workflowType: "weekly-planning",
      title: isReview ? "Weekly Review" : "Weekly Planning",
      summary: isReview ? "Turn the week into a useful review with wins, blockers, and the next best focus." : "Create a practical plan with priorities, workload, and the next best focus.",
      prompt: isReview ? `Review the week for: ${request}` : `Create a planning pass for: ${request}`,
      taskTitle: isReview ? "Review the week" : action.includes("tomorrow") ? "Plan tomorrow" : "Plan the week",
      taskDescription: isReview ? "Create a weekly review note with wins, blockers, completed work, and next-week focus." : action.includes("tomorrow") ? "Create a concrete tomorrow plan with schedule, priorities, and preparation blocks." : "Create a practical weekly plan with priorities, workload, and next actions.",
      noteTitle: isReview ? `Weekly review • ${shorten(request)}` : action.includes("tomorrow") ? `Tomorrow plan • ${shorten(request)}` : `Weekly plan • ${shorten(request)}`,
      noteBody: "",
      actionLabel: isReview ? "Review week" : action.includes("tomorrow") ? "Plan tomorrow" : "Plan week",
    };
  }

  if (normalized.includes("document") || normalized.includes("summarize") || action.includes("summarize")) {
    return {
      workflowType: "summarize-documents",
      title: "Summarize Documents",
      summary: "Turn the request into a clear, usable summary with key takeaways and next steps.",
      prompt: `Summarize the documents or notes related to: ${request}`,
      taskTitle: "Summarize documents",
      taskDescription: "Create a structured summary with key takeaways and action items.",
      noteTitle: `Document summary • ${shorten(request)}`,
      noteBody: "",
      actionLabel: "Summarize docs",
    };
  }

  if (normalized.includes("calendar") || normalized.includes("schedule") || action.includes("schedule") || action.includes("block")) {
    return {
      workflowType: "calendar-planning",
      title: "Calendar Planning",
      summary: "Turn the request into a focused calendar plan with prep blocks and time protection.",
      prompt: `Plan the calendar around: ${request}`,
      taskTitle: "Plan your calendar",
      taskDescription: "Turn the request into a practical calendar plan with prep blocks and time protection.",
      noteTitle: `Calendar plan • ${shorten(request)}`,
      noteBody: "",
      actionLabel: "Plan calendar",
    };
  }

  return {
    workflowType: "general-planning",
    title: "Plan the next step",
    summary: "Turn the request into a focused artifact with clear next steps.",
    prompt: `Help me act on this request: ${request}`,
    taskTitle: "Capture the next action",
    taskDescription: "Create a concrete task and follow-up note from the request.",
    noteTitle: `Action note • ${shorten(request)}`,
    noteBody: "",
    actionLabel: "Create action",
  };
}

function buildContextSnapshot({ dashboard, goals, projects, notes, calendar, understanding }: { dashboard: Dashboard | null; goals: Goal[]; projects: Project[]; notes: Note[]; calendar: CalendarContext | null; understanding: MemoryTrustRecord[] }) {
  const mission = firstString(dashboard?.personal_os?.current_mission) || firstString(dashboard?.personal_os?.suggested_next_action?.title) || "your current priorities";
  const focus = firstString(dashboard?.daily?.focus_areas?.[0]) || firstString(dashboard?.personal_os?.current_focus) || "the highest-value work";
  const currentGoal = firstString(goals?.[0]?.title) || firstString(goals?.[0]?.description) || firstString(dashboard?.daily?.focus_areas?.[1]) || "your active goals";
  const currentProject = firstString(projects?.[0]?.name) || firstString(dashboard?.projects?.[0]?.name) || "your current projects";
  const recentNoteTopics = notes.slice(0, 3).map((note) => stripToWords(firstString(note?.title) || firstString(note?.content), 24)).filter(Boolean);
  const memorySignals = understanding.slice(0, 3).map((item) => stripToWords(firstString(item?.content), 24)).filter(Boolean);
  const calendarSignals = [
    ...(calendar?.today || []).slice(0, 2).map((event) => firstString(event?.title)),
    ...(calendar?.conflicts || []).slice(0, 2),
  ].filter(Boolean);
  const recentActivity = [
    ...(dashboard?.recent_activity || []).slice(0, 3).map((activity) => firstString(activity?.title || activity?.description)),
    ...(dashboard?.memory_evolution || []).slice(0, 2),
  ].filter(Boolean);
  const priorities = [
    ...(dashboard?.personal_os?.top_priorities || []).slice(0, 3).map((item) => firstString(item?.title || item?.detail)),
    ...(dashboard?.daily?.focus_areas || []).slice(0, 2),
  ].filter(Boolean);

  return {
    mission,
    focus,
    currentGoal,
    currentProject,
    recentNoteTopics,
    memorySignals,
    calendarSignals,
    calendarLoadMinutes: calendar?.meetingLoadMinutes || 0,
    requestContext: [mission, focus, currentGoal, currentProject].filter(Boolean).join(" • "),
    recentActivity,
    priorities,
  };
}

export function buildWorkflowContent(workflowType: string, request: string, context: ReturnType<typeof buildContextSnapshot>) {
  const baseContext = [
    `Mission: ${context.mission}`,
    `Focus: ${context.focus}`,
    `Goal: ${context.currentGoal}`,
    `Project: ${context.currentProject}`,
  ].join("\n");
  const isWeeklyReview = workflowType === "weekly-planning" && /review|weekly review/i.test(request);

  if (workflowType === "prepare-podcast") {
    return [
      `# Podcast prep for ${request}`,
      "",
      "## Guest summary",
      `The strongest version of this conversation is grounded in ${context.mission} and tied directly to ${context.currentProject}. It should feel useful to your audience, not generic or promotional.`,
      "",
      "## Previous interactions",
      ...context.memorySignals.length ? context.memorySignals.map((item) => `- ${item}`) : ["- No prior memory signals were surfaced, so the prep is anchored in your current mission and active project."],
      "",
      "## Key topics",
      `- ${request}`,
      `- How this connects to ${context.currentProject}`,
      `- What matters most for ${context.currentGoal}`,
      `- One concrete example or story that makes the lesson tangible`,
      "",
      "## Personalized introduction",
      `Open by framing the topic around ${context.focus} and why it matters now. Make the listener feel that this is a practical conversation for ${context.currentGoal}, not a rehearsed monologue.`,
      "",
      "## 15 interview questions",
      ...Array.from({ length: 15 }, (_, index) => `${index + 1}. ${buildQuestionPrompt(request, index, context)}`),
      "",
      "## Follow-up questions",
      "- What changed since the last time you discussed this?",
      "- What would make this most useful for the audience?",
      "- What should we make explicit before we close?",
      "",
      "## Episode outline",
      "1. Opening with the real-world context",
      "2. Why this matters now",
      "3. The clearest insight or example",
      "4. A practical takeaway for listeners",
      "5. Close with a concrete next step",
      "",
      "## Publishing checklist",
      "- Confirm the central thesis before recording",
      "- Make sure the opening sounds personal and concise",
      "- Prepare one concrete takeaway",
      "- Note the follow-up action before you finish",
      "- Capture one strong quote or hook for social clips",
      "",
      "## Social media teaser",
      `A strong teaser would be: ${request} framed through ${context.mission} in a way that feels immediately useful and grounded in ${context.currentProject}.`,
      "",
      "## Context used",
      baseContext,
    ].join("\n");
  }

  if (workflowType === "prepare-meeting") {
    return [
      `# Meeting brief for ${request}`,
      "",
      "## Why we are meeting",
      `The purpose is to move ${request} forward with a clear decision point, a short list of tradeoffs, and a practical next action.`,
      "",
      "## Previous context",
      ...context.recentNoteTopics.length ? context.recentNoteTopics.map((topic) => `- ${topic}`) : ["- No recent notes were surfaced, so the brief leans on the current mission and active project."],
      ...context.memorySignals.length ? ["", "### Relevant memory", ...context.memorySignals.map((signal) => `- ${signal}`)] : [],
      ...context.recentActivity.length ? ["", "### Recent activity", ...context.recentActivity.slice(0, 3).map((activity) => `- ${activity}`)] : [],
      "",
      "## Who is attending",
      `Use the current project context around ${context.currentProject} and your active goal of ${context.currentGoal} to shape the right level of detail for the room.`,
      ...context.calendarSignals.length ? ["", "### Calendar context", ...context.calendarSignals.map((signal) => `- ${signal}`)] : [],
      "",
      "## Decisions required",
      "- What should be prioritized now",
      "- What should be deferred",
      "- Who owns the follow-up",
      "- What should be closed before the next touchpoint",
      "",
      "## Questions to ask",
      "- What matters most right now",
      "- What could block momentum",
      "- What evidence would change the decision",
      "- What would make the next step materially easier",
      "",
      "## Risks and constraints",
      "- The topic could drift into general discussion without a decision",
      "- The follow-up may get lost unless it is captured immediately",
      "- Calendar pressure may limit preparation time",
      "- The current constraint may be organizational rather than technical",
      "",
      "## Follow-up",
      "- Send a concise recap after the meeting",
      "- Capture the decision in Synzept",
      "- Schedule the next check-in if needed",
      "",
      "## Context used",
      baseContext,
    ].join("\n");
  }

  if (workflowType === "draft-email") {
    return [
      `# Email draft for ${request}`,
      "",
      "## Subject line",
      `A strong subject line could be: ${buildSubjectLine(request, context)}`,
      "",
      "## Email body",
      `${buildEmailBody(request, context)}`,
      "",
      "## Clear call to action",
      "- State the specific next step",
      "- Keep the request easy to act on",
      "- Include a useful deadline or option if appropriate",
      "- Make the outcome feel low-friction and concrete",
      "",
      "## Alternative tone options",
      "- Friendly and warm",
      "- Direct and concise",
      "- Calm and executive",
      "",
      "## Suggested follow-up",
      "- Send a short reminder if no response arrives within a few days",
      "- Keep the follow-up focused on the next action",
      "- Offer a simple fallback if the timing is not right",
      "",
      "## Context used",
      baseContext,
    ].join("\n");
  }

  if (workflowType === "weekly-planning") {
    if (isWeeklyReview) {
      return [
        `# Weekly review for ${request}`,
        "",
        "## Wins",
        `- Capture the outcomes that mattered most this week for ${context.currentGoal}`,
        "- Note the progress that was meaningful even if it was not dramatic",
        "",
        "## Progress",
        `- Highlight the work that moved ${context.currentProject} forward`,
        `- Reference the most relevant notes and memory signals that shaped the week`,
        "",
        "## Completed work",
        "- Note the tasks or decisions that are now closed",
        "- Call out anything that should be preserved for future reference",
        "",
        "## Blockers",
        "- Identify what slowed momentum this week",
        "- Note the constraints that are likely to reappear",
        "",
        "## Open loops",
        "- Capture anything still unresolved or waiting for attention",
        "- Keep the next step visible so it does not disappear",
        "",
        "## Recommended focus for next week",
        `Focus next week on ${context.focus} while keeping ${context.currentGoal} as the guide and ${context.currentProject} as the context for execution.`,
        "",
        "## Context used",
        baseContext,
      ].join("\n");
    }

    const workloadLabel = context.calendarLoadMinutes > 240 ? "heavy" : context.calendarLoadMinutes > 120 ? "moderate" : "light";
    return [
      `# ${context.calendarLoadMinutes ? "Tomorrow" : "Weekly"} plan for ${request}`,
      "",
      "## Calendar",
      context.calendarSignals.length ? `Use the current calendar signals (${context.calendarSignals.slice(0, 3).join(", ")}) to protect high-value work and leave buffer time before reactive tasks.` : "Keep the schedule flexible if no calendar commitments are currently visible.",
      "",
      "## Deep work blocks",
      `- Protect one uninterrupted block for the hardest work tied to ${context.currentGoal}`,
      `- Keep one lighter block for review and follow-up on ${context.currentProject}`,
      "- Reserve a short reset before meetings or calls",
      "",
      "## Preparation time",
      "- Set aside 15–20 minutes to collect the materials you need before the day begins",
      "- Leave a short buffer for last-minute updates or stakeholder requests",
      "",
      "## Personal priorities",
      ...context.priorities.length ? context.priorities.slice(0, 3).map((priority) => `- ${priority}`) : ["- Keep the day anchored to the highest-value outcome."],
      ...context.recentActivity.length ? ["", "## Recent activity", ...context.recentActivity.slice(0, 3).map((activity) => `- ${activity}`)] : [],
      "",
      "## Task ordering",
      "1. Start with the work that materially advances the most important outcome",
      "2. Handle the work that reduces risk or closes a dependency",
      "3. Leave the final block for follow-up, response, or cleanup",
      "",
      "## Energy-aware schedule",
      `The day should start with ${context.focus}, then move into the work that needs the clearest thinking, and leave the final stretch for lighter or administrative tasks.`,
      "",
      "## Estimated completion",
      `This plan should leave the day feeling ${workloadLabel} and realistic, with enough margin to finish the highest-value work without overcommitting.`,
      "",
      "## Context used",
      baseContext,
    ].join("\n");
  }

  return [
    `# Action note for ${request}`,
    "",
    "## What to do",
    `Use ${context.currentProject} and ${context.currentGoal} as the anchor for the next clear step.`,
    "",
    "## Suggested structure",
    "- Write the next concrete action",
    "- Note any dependencies",
    "- Capture the likely outcome",
    "",
    "## Context used",
    baseContext,
  ].join("\n");
}

function buildTaskDescription(workflowType: string, request: string, context: ReturnType<typeof buildContextSnapshot>) {
  if (workflowType === "prepare-podcast") {
    return `Prepared a podcast brief for ${request} using your current mission, focus, and project context (${context.currentProject}).`;
  }
  if (workflowType === "prepare-meeting") {
    return `Prepared a meeting brief for ${request} using your current goal, project context, and likely decision points.`;
  }
  if (workflowType === "draft-email") {
    return `Prepared an email draft for ${request} with a usable subject, body, CTA, and follow-up direction.`;
  }
  if (workflowType === "weekly-planning") {
    return `Prepared a schedule and prioritization plan for ${request} that keeps the next step aligned with your active work.`;
  }
  return `Prepared a structured action artifact for ${request} using your current mission and project context.`;
}

function buildQuestionPrompt(request: string, index: number, context: ReturnType<typeof buildContextSnapshot>) {
  const prompts = [
    `What is the most important insight about ${request}?`,
    `What would make this immediately useful for your audience?`,
    `How does this connect to ${context.currentProject}?`,
    `What is the best example you can share?`,
    `What do you want the listener to leave with?`,
  ];
  return prompts[index % prompts.length];
}

function buildSubjectLine(request: string, context: ReturnType<typeof buildContextSnapshot>) {
  return `${request} • ${context.currentGoal}`;
}

function buildEmailBody(request: string, context: ReturnType<typeof buildContextSnapshot>) {
  return [
    `Hi,`,
    "",
    `I wanted to follow up on ${request} and make sure we are aligned on the next step.`,
    `The current focus is ${context.focus}, and the most useful next move is to keep this moving in a way that supports ${context.currentGoal}.`,
    "",
    "Please let me know if you want me to draft a tighter version or if you would prefer to handle it directly.",
    "",
    "Thanks,",
    "Synzept",
  ].join("\n");
}

function firstString(value: unknown) {
  return typeof value === "string" && value.trim() ? value.trim() : "";
}

function stripToWords(value: string, limit = 24) {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  const words = normalized.split(" ");
  if (words.length <= limit) return normalized;
  return `${words.slice(0, limit).join(" ")}…`;
}

function shorten(value: string) {
  const trimmed = value.trim();
  if (!trimmed) return "next step";
  return trimmed.length > 34 ? `${trimmed.slice(0, 31)}...` : trimmed;
}

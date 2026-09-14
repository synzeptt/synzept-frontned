export type ChiefOfStaffApprovalItem = {
  id: string;
  title: string;
  description: string;
  status: string;
};

export type ChiefOfStaffWaitingItem = {
  title: string;
  detail: string;
  owner?: string;
};

export type ChiefOfStaffCompletedItem = {
  title: string;
  detail: string;
};

export type ChiefOfStaffRiskItem = {
  title: string;
  detail: string;
  severity: "High" | "Medium" | "Low";
};

export type ChiefOfStaffDecisionSupport = {
  title: string;
  context: string[];
  options: string[];
  pros: string[];
  cons: string[];
  recommendation: string;
  evidence: string[];
  suggestedNextStep: string;
};

export type ChiefOfStaffCommandCenterSnapshot = {
  greeting: string;
  mission: string;
  priorities: string[];
  approvalQueue: ChiefOfStaffApprovalItem[];
  waitingOnOthers: ChiefOfStaffWaitingItem[];
  recentlyCompleted: ChiefOfStaffCompletedItem[];
  upcomingRisks: ChiefOfStaffRiskItem[];
  decisionSupport: ChiefOfStaffDecisionSupport;
  quickActions: Array<{ title: string; description: string }>;
};

export function buildChiefOfStaffCommandCenter(input: {
  mission?: string;
  focusAreas?: string[];
  tasks?: Array<{ title: string; description?: string; priority?: string; due_at?: string }>; 
  notes?: Array<{ title?: string; content?: string; tags?: string[] }>;
  completedToday?: string[];
  projects?: Array<{ name?: string; description?: string }>;
  approvals?: ChiefOfStaffApprovalItem[];
}): ChiefOfStaffCommandCenterSnapshot {
  const priorities = (input.focusAreas?.length ? input.focusAreas : [input.mission || "Keep the work moving"]).slice(0, 3);
  const approvalQueue = (input.approvals?.length ? input.approvals : [
    { id: "approve-1", title: "Approve meeting notes", description: "The summary is ready for your review.", status: "Ready to review" },
    { id: "approve-2", title: "Confirm tomorrow's schedule", description: "The plan should be approved before the day begins.", status: "Ready to review" },
  ]).slice(0, 3);

  const waitingOnOthers = [
    ...(input.tasks || []).filter((task) => /waiting|pending|review|confirm|reply/i.test(task.title + " " + (task.description || ""))).map((task) => ({ title: task.title, detail: task.description || "This work depends on someone else to move forward.", owner: "Waiting on others" })),
    ...(input.notes || []).filter((note) => /waiting|pending|reply|review/i.test((note.title || "") + " " + (note.content || ""))).map((note) => ({ title: note.title || "Follow-up pending", detail: note.content || "This is still waiting for external input.", owner: "Waiting on others" })),
  ].slice(0, 3);

  const recentlyCompleted = (input.completedToday?.length ? input.completedToday : ["Prepared the next set of actions", "Captured the latest context"]).map((item, index) => ({ title: index === 0 ? `Completed: ${item}` : item, detail: "Synzept finished this for you already." })).slice(0, 4);
  const risks = [
    {
      title: "Upcoming deadline",
      detail: input.tasks?.[0]?.title ? `A deadline is approaching around ${input.tasks[0].title}.` : "A high-priority commitment needs attention soon.",
      severity: "High" as const,
    },
    {
      title: "Review pending",
      detail: input.notes?.[0]?.title ? `${input.notes[0].title} still needs a human decision.` : "A key review is still open.",
      severity: "Medium" as const,
    },
    {
      title: "Calendar pressure",
      detail: input.projects?.[0]?.name ? `${input.projects[0].name} is at risk of consuming too much attention this week.` : "The schedule is getting crowded.",
      severity: "Medium" as const,
    },
  ].slice(0, 3);

  return {
    greeting: "Good morning",
    mission: input.mission || "Keep the work moving without surprise.",
    priorities,
    approvalQueue,
    waitingOnOthers: waitingOnOthers.length ? waitingOnOthers : [{ title: "Client reply pending", detail: "A reply is still needed before the next step can happen.", owner: "External" }],
    recentlyCompleted,
    upcomingRisks: risks,
    decisionSupport: {
      title: "Decision support",
      context: ["Recent context suggests urgency is rising.", "The current plan is still viable but needs clarity."],
      options: ["Proceed with the current plan", "Pause for a more informed review"],
      pros: ["Keeps momentum", "Reduces unnecessary friction"],
      cons: ["May add pressure later", "Could create rework"],
      recommendation: "Proceed with the current plan, but only after the most important approval is handled.",
      evidence: ["The strongest signal from your workspace is momentum.", "The next approval is small and low-risk."],
      suggestedNextStep: "Approve the highest-value item and let the rest follow automatically.",
    },
    quickActions: [
      { title: "Approve prepared work", description: "Review the current approvals and keep momentum moving." },
      { title: "Review open risks", description: "Look at the items that could turn into larger problems." },
      { title: "Prepare the next follow-up", description: "Turn the latest context into one small, useful action." },
    ],
  };
}

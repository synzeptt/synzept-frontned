import type { OpenLoopEngineItem } from "@/lib/api";

const today = new Date().toISOString();
const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();

export const sampleProjects = [
  {
    id: "sample-onboarding-redesign",
    name: "Onboarding Redesign",
    description: "Improve the first-run experience so new users understand Synzept in minutes.",
    currentFocus: "Turn the blank dashboard into a guided continuation workspace.",
    recommendedNextStep: "Draft the first three onboarding prompts and connect them to starter projects.",
    status: "active",
    created_at: threeDaysAgo,
    createdAt: threeDaysAgo,
    updatedAt: today,
    context_summary: "The project is focused on reducing first-session friction.",
  },
  {
    id: "sample-launch-plan",
    name: "Product Launch Plan",
    description: "Coordinate pricing, download links, and release messaging for Synzept Pro.",
    currentFocus: "Verify the upgrade flow and make Pro value visible from pricing.",
    recommendedNextStep: "Review the payment checkout copy and test the Razorpay path.",
    status: "active",
    created_at: threeDaysAgo,
    createdAt: threeDaysAgo,
    updatedAt: yesterday,
    context_summary: "Launch readiness depends on billing confidence and clear user education.",
  },
];

export const sampleDailyBrief = {
  whatMattersToday: [
    {
      title: "Finish the onboarding examples",
      detail: "New users should see useful projects, open loops, and next steps before they create anything.",
      priority: "high",
      href: "/projects",
    },
    {
      title: "Verify the Pro checkout path",
      detail: "Pricing should lead to billing, Razorpay checkout, then verified activation.",
      priority: "high",
      href: "/billing",
    },
  ],
  openLoops: [
    {
      title: "Decide which starter project template appears first",
      detail: "Choose between Launch Plan, Client Project, Study Plan, or Personal System.",
      priority: "medium",
      href: "/open-loops",
    },
    {
      title: "Follow up on mobile app Google sign-in",
      detail: "Confirm Android OAuth fingerprints are registered before the next APK release.",
      priority: "medium",
      href: "/open-loops",
    },
  ],
  recentProgress: [
    {
      title: "Pricing page updated",
      detail: "Synzept Pro is now shown at Rs 399/month with payment-first language.",
      priority: "low",
      href: "/pricing",
    },
    {
      title: "Billing shortcut removed",
      detail: "Pro access now requires Razorpay verification before activation.",
      priority: "low",
      href: "/billing",
    },
  ],
  projectsNeedingAttention: [
    {
      title: "Android APK release",
      detail: "Needs final Google sign-in verification on device.",
      priority: "medium",
      href: "/projects",
    },
  ],
  contextToRemember: [
    {
      title: "Synzept should answer: what should I focus on right now?",
      detail: "Daily Brief, Open Loops, Timeline, and Project Intelligence all support this promise.",
      priority: "medium",
      href: "/daily-brief",
    },
  ],
  recommendedNextStep: {
    title: "Create starter examples for empty workspaces",
    detail: "This gives new users an immediate feel for Daily Brief, Open Loops, Timeline, and project continuity.",
    href: "/projects",
  },
};

export const sampleOpenLoops: OpenLoopEngineItem[] = [
  {
    id: "sample-loop-onboarding-copy",
    source: "task",
    sourceId: "sample-loop-onboarding-copy",
    title: "Write the welcome copy for first-time users",
    description: "The dashboard should explain continuity through real examples, not an empty placeholder.",
    projectId: "sample-onboarding-redesign",
    projectName: "Onboarding Redesign",
    type: "unfinished_task",
    status: "open",
    createdAt: today,
    updatedAt: today,
    priority: "high",
    href: "/projects",
    nextStep: "Draft three short starter prompts.",
  },
  {
    id: "sample-loop-billing-decision",
    source: "decision",
    sourceId: "sample-loop-billing-decision",
    title: "Choose the billing success redirect copy",
    description: "The user should know Pro was unlocked only after payment verification.",
    projectId: "sample-launch-plan",
    projectName: "Product Launch Plan",
    type: "pending_decision",
    status: "open",
    createdAt: yesterday,
    updatedAt: yesterday,
    priority: "medium",
    href: "/billing",
    nextStep: "Review the dashboard success message.",
  },
  {
    id: "sample-loop-android-oauth",
    source: "note",
    sourceId: "sample-loop-android-oauth",
    title: "Confirm Android OAuth fingerprints",
    description: "Google sign-in needs package name, SHA-1, and SHA-256 registered in Google Cloud.",
    projectId: "sample-launch-plan",
    projectName: "Android APK Release",
    type: "follow_up",
    status: "open",
    createdAt: threeDaysAgo,
    updatedAt: yesterday,
    priority: "medium",
    href: "/timeline",
    nextStep: "Test account picker on the installed APK.",
  },
];

export const sampleTasks = [
  {
    id: "sample-task-brief",
    title: "Review today's Daily Brief",
    description: "Scan what matters, open loops, and the recommended next step before starting new work.",
    status: "todo",
    priority: "high",
    project_id: null,
    due_at: today,
    created_at: today,
  },
  {
    id: "sample-task-loop",
    title: "Turn one open loop into a next action",
    description: "Pick an unfinished item and decide whether to complete, snooze, or ignore it.",
    status: "todo",
    priority: "medium",
    project_id: null,
    due_at: null,
    created_at: today,
  },
];


export const sampleTimelineItems = [
  {
    id: "sample-timeline-billing",
    title: "Billing verification hardened",
    detail: "Pro activation now depends on Razorpay payment success and signature verification.",
    date: today,
    href: "/billing",
    type: "decision",
  },
  {
    id: "sample-timeline-pricing",
    title: "Synzept Pro pricing clarified",
    detail: "The Pro plan is positioned at Rs 399/month with Daily Brief, Open Loops, and Project Intelligence.",
    date: yesterday,
    href: "/pricing",
    type: "milestone",
  },
  {
    id: "sample-timeline-open-loop",
    title: "Open loop created for Android sign-in",
    detail: "Google OAuth still needs Android package and certificate verification before release.",
    date: threeDaysAgo,
    href: "/open-loops",
    type: "follow_up",
  },
];

export const sampleProjectTemplates = [
  {
    name: "Product Launch Plan",
    description: "Plan a release with pricing, messaging, checkout, and post-launch follow-up.",
    currentFocus: "Make the launch path clear from landing page to payment to dashboard.",
    recommendedNextStep: "List the launch blockers and assign one next action to each.",
  },
  {
    name: "Client Project",
    description: "Track deliverables, decisions, waiting items, and next steps for a client engagement.",
    currentFocus: "Clarify the current deliverable and the next client-facing milestone.",
    recommendedNextStep: "Record the latest client decision and any waiting response.",
  },
  {
    name: "Study Plan",
    description: "Organize learning goals, notes, unfinished topics, and weekly review items.",
    currentFocus: "Identify the topic that needs attention today.",
    recommendedNextStep: "Turn one weak topic into a short review task.",
  },
];

export const sampleOnboardingExamples = {
  goals: ["Launch Synzept Pro", "Improve onboarding", "Ship Android APK"],
  priorities: ["Verify checkout", "Create starter examples", "Review open loops"],
  firstNote: "Remember: Synzept is most useful when each project has a current focus, open loops, decisions, and one recommended next step.",
};

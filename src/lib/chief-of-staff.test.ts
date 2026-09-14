import test from "node:test";
import assert from "node:assert/strict";
import { buildChiefOfStaffCommandCenter } from "./chief-of-staff";

test("command center snapshot turns context into approval, risk, and decision surfaces", () => {
  const snapshot = buildChiefOfStaffCommandCenter({
    focusAreas: ["Launch readiness"],
    mission: "Ship the launch without surprises",
    tasks: [
      { title: "Review launch notes", description: "Pending review from stakeholders", priority: "high", due_at: "2026-07-23T00:00:00.000Z" },
      { title: "Client reply", description: "Waiting on client confirmation", priority: "medium" },
    ],
    notes: [
      { title: "Weekly review draft", content: "Needs approval before publishing", tags: ["review"] },
      { title: "Follow-up email", content: "Awaiting client response", tags: ["waiting"] },
    ],
    completedToday: ["Summarized the launch sync", "Created follow-up tasks"],
    projects: [{ name: "Launch", description: "Milestone approaching" }],
    approvals: [{ id: "review-1", title: "Publish weekly review", description: "Ready for approval", status: "Ready to review" }],
  } satisfies Parameters<typeof buildChiefOfStaffCommandCenter>[0]);

  assert.ok(snapshot.approvalQueue.length > 0);
  assert.ok(snapshot.waitingOnOthers.some((item) => item.title.includes("Client")));
  assert.ok(snapshot.recentlyCompleted.some((item) => item.title.includes("Summarized")));
  assert.ok(snapshot.upcomingRisks.some((item) => item.title.includes("deadline") || item.title.includes("review")));
  assert.ok(snapshot.decisionSupport.recommendation);
  assert.ok(snapshot.quickActions.length >= 3);
});

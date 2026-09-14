import test from "node:test";
import assert from "node:assert/strict";
import { buildWorkflowContent, buildWorkflowExecutionPlan } from "./ai-workflows";
import { buildDailyExecutiveBriefExperience, buildMeetingAssistantExperience, buildWeeklyExecutiveReviewSnapshot } from "./flagship-experiences";

test("meeting briefs include context-driven sections", () => {
  const context = {
    mission: "Launch the new product",
    focus: "Close the launch blockers",
    currentGoal: "Ship v2 on time",
    currentProject: "Northstar launch",
    recentNoteTopics: ["Launch blockers", "Partner follow-up"],
    memorySignals: ["Stakeholder confidence is fragile", "Legal review is the blocker"],
    calendarSignals: ["Leadership sync", "Legal review"],
    calendarLoadMinutes: 180,
    requestContext: "Launch the new product • Close the launch blockers",
    recentActivity: ["Reviewed launch blockers", "Updated partner follow-up"],
    priorities: ["Resolve legal review", "Confirm launch readout"],
  };

  const body = buildWorkflowContent("prepare-meeting", "Launch sync with leadership", context satisfies Parameters<typeof buildWorkflowContent>[2]);

  assert.match(body, /## Why we are meeting/);
  assert.match(body, /## Previous context/);
  assert.match(body, /## Decisions required/);
  assert.match(body, /## Questions to ask/);
  assert.match(body, /## Risks and constraints/);
  assert.match(body, /## Follow-up/);
  assert.match(body, /Launch blockers/);
  assert.match(body, /Leadership sync/);
});

test("tomorrow plans include energy-aware scheduling and task ordering", () => {
  const context = {
    mission: "Protect deep work",
    focus: "Finish the quarter plan",
    currentGoal: "Prepare the board update",
    currentProject: "Board prep",
    recentNoteTopics: ["Board messaging"],
    memorySignals: ["Mornings are best for writing"],
    calendarSignals: ["Board prep review"],
    calendarLoadMinutes: 240,
    requestContext: "Protect deep work • Finish the quarter plan",
    recentActivity: ["Drafted the executive update"],
    priorities: ["Draft the board narrative", "Finalize the metrics deck"],
  };

  const body = buildWorkflowContent("weekly-planning", "Tomorrow plan", context satisfies Parameters<typeof buildWorkflowContent>[2]);

  assert.match(body, /## Calendar/);
  assert.match(body, /## Deep work blocks/);
  assert.match(body, /## Preparation time/);
  assert.match(body, /## Personal priorities/);
  assert.match(body, /## Task ordering/);
  assert.match(body, /## Energy-aware schedule/);
  assert.match(body, /board narrative/);
});

test("workflow execution plans expose the next useful action and status", () => {
  const plan = buildWorkflowExecutionPlan("prepare-meeting", "Launch sync", { currentProject: "Northstar launch", focus: "Close launch blockers" });
  assert.equal(plan.status, "Ready");
  assert.match(plan.nextActionLabel, /Create action items/i);
  assert.match(plan.nextActionDescription, /follow-up/i);

  const tomorrowPlan = buildWorkflowExecutionPlan("weekly-planning", "Tomorrow plan", { currentProject: "Board prep", focus: "Finish the quarter plan" });
  assert.equal(tomorrowPlan.status, "Ready");
  assert.match(tomorrowPlan.nextActionLabel, /Reserve focus blocks/i);
});

test("meeting assistant snapshots produce executive prep with clear next steps", () => {
  const snapshot = buildMeetingAssistantExperience({
    meetingName: "Leadership sync",
    objective: "Align on launch readiness",
    agenda: ["Confirm launch blockers", "Review ownership"],
    decisionsRequired: ["What needs to happen before launch?"],
    actionItems: ["Create the launch checklist"],
  });

  assert.equal(snapshot.title, "Leadership sync");
  assert.match(snapshot.objective, /launch readiness/i);
  assert.ok(snapshot.agenda.includes("Confirm launch blockers"));
  assert.ok(snapshot.decisionsRequired.some((item) => item.includes("launch")));
});

test("daily and weekly executive snapshots stay action oriented", () => {
  const daily = buildDailyExecutiveBriefExperience({
    headline: "The day is already scoped",
    recommendedFocus: "Protect the launch review",
    preparedDeliverables: ["Launch review prep"],
    quickWins: ["Close one blocker"],
  });

  const weekly = buildWeeklyExecutiveReviewSnapshot({
    headline: "The week had a clear path",
    wins: ["Closed the timeline review"],
    suggestedPriorities: ["Protect the launch review"],
  });

  assert.match(daily.headline, /scoped/i);
  assert.equal(daily.recommendedFocus, "Protect the launch review");
  assert.equal(weekly.headline, "The week had a clear path");
  assert.ok(weekly.suggestedPriorities.includes("Protect the launch review"));
});

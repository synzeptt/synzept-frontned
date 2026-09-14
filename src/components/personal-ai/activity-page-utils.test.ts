import assert from "node:assert/strict";
import test from "node:test";
import { filterActivitiesByQueryAndCategory, getPeriodLabel, type ActivityItem } from "./activity-page-utils";

test("filters activity items by category and text search", () => {
  const items: ActivityItem[] = [
    {
      id: "1",
      type: "files",
      category: "files",
      title: "Uploaded file",
      description: "Business plan summary",
      timestamp: "2026-08-07T10:00:00.000Z",
      status: "completed",
      metadata: { fileName: "Business_Plan.pdf" },
    },
    {
      id: "2",
      type: "ai",
      category: "ai",
      title: "AI response completed",
      description: "Generated a report for launch readiness",
      timestamp: "2026-08-07T10:05:00.000Z",
      status: "completed",
      metadata: { conversationName: "Launch prep" },
    },
  ];

  const results = filterActivitiesByQueryAndCategory(items, "plan", "files");

  assert.equal(results.length, 1);
  assert.equal(results[0].id, "1");
});

test("assigns the right period label for recent and older activity", () => {
  const now = new Date("2026-08-07T12:00:00.000Z");

  assert.equal(getPeriodLabel(new Date("2026-08-07T11:30:00.000Z"), now), "Today");
  assert.equal(getPeriodLabel(new Date("2026-08-06T11:30:00.000Z"), now), "Yesterday");
  assert.equal(getPeriodLabel(new Date("2026-08-02T11:30:00.000Z"), now), "Earlier This Week");
  assert.equal(getPeriodLabel(new Date("2026-07-29T11:30:00.000Z"), now), "Last Week");
  assert.equal(getPeriodLabel(new Date("2026-07-10T11:30:00.000Z"), now), "Older");
});

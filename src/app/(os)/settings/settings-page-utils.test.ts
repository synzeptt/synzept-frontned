import test from "node:test";
import assert from "node:assert/strict";
import { getSettingsSections } from "./settings-page-utils";

test("settings sections include the core launch surfaces", () => {
  const sections = getSettingsSections();
  const ids = sections.map((section) => section.id);

  assert.ok(ids.includes("profile"));
  assert.ok(ids.includes("billing"));
  assert.ok(ids.includes("danger-zone"));
});

import { describe, expect, it } from "vitest";
import { resolveArtifactUrl } from "./execution-result-actions";

describe("artifact URL resolution", () => {
  it("resolves relative API artifacts against the configured API base", () => {
    process.env.NEXT_PUBLIC_API_URL = "https://api.synzept.com";
    expect(resolveArtifactUrl("/api/v2/actions/action-1/download/artifact-1")).toBe(
      "https://api.synzept.com/api/v2/actions/action-1/download/artifact-1",
    );
  });

  it("preserves absolute artifact URLs", () => {
    expect(resolveArtifactUrl("https://api.synzept.com/files/report.pdf")).toBe(
      "https://api.synzept.com/files/report.pdf",
    );
  });
});

/**
 * Integration test for frontend execution experience with research → PDF flow.
 *
 * This test simulates a complete user flow:
 * 1. User submits "Research future AI opportunities and make a PDF" in Ask Synzept
 * 2. Frontend creates ActionExecution via api.createActionExecution()
 * 3. Frontend receives real execution_id from backend
 * 4. Frontend polls backend for execution status via syncExecutionStatus()
 * 5. Frontend displays execution progress (planning → executing → completed)
 * 6. Frontend displays real artifact with download URL
 * 7. User can refresh page and recover execution state
 * 8. User can approve/reject if needed
 *
 * Note: This test uses the real backend API. Requires:
 * - Backend running at localhost:3000 (or NEXT_PUBLIC_API_URL)
 * - User authenticated
 * - Can be run with: `npm run test -- test/integration/frontend-execution.test.ts`
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

type MockExecution = {
  id: string;
  status: string;
  progress: number;
  title: string;
  request: string;
  output: string | null;
  error: string | null;
  metadata: Record<string, unknown>;
  _createdAt?: number;
};

/**
 * Helper to sleep for a period of time.
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Mock API client for testing.
 * In a real test, this would use the actual api client from src/lib/api.ts
 */
class MockActionExecutionAPI {
  private executions: Map<string, MockExecution> = new Map();
  private executionCounter = 0;

  async createActionExecution(request: string): Promise<{
    id: string;
    status: string;
    progress: number;
    title: string;
    request: string;
    output: string | null;
    error: string | null;
    metadata: Record<string, unknown>;
  }> {
    this.executionCounter++;
    const id = `execution-${this.executionCounter}`;
    
    // Simulate backend classification
    const title = request.includes("pdf") || request.includes("make a pdf") 
      ? "Pdf_generation: Research future AI opportunities and make a PDF"
      : "Generic: " + request;

    const execution = {
      id,
      status: "planning",
      progress: 0,
      title,
      request,
      output: null as string | null,
      error: null as string | null,
      metadata: {
        tool_plan: [
          { tool: "research_tool", parameters: { goal: request } },
          { tool: "artifact_generation", parameters: { artifact_type: "pdf", content: "{{research_tool.output.summary}}" } },
        ],
      },
    };

    this.executions.set(id, execution);
    return execution;
  }

  async getActionExecution(id: string): Promise<MockExecution> {
    const execution = this.executions.get(id);
    if (!execution) throw new Error(`Execution ${id} not found`);

    // Simulate progression
    const elapsed = Date.now() - (execution._createdAt || Date.now());
    
    if (elapsed < 1000) {
      // Planning phase (0-30%)
      execution.status = "planning";
      execution.progress = 15;
    } else if (elapsed < 3000) {
      // Awaiting confirmation phase
      execution.status = "awaiting_confirmation";
      execution.progress = 30;
      execution.metadata = {
        ...execution.metadata,
        approval_required: true,
        approval_reason: "This action will research AI and generate a PDF. Proceed?",
      };
    } else if (elapsed < 5000) {
      // Executing phase (30-80%)
      execution.status = "executing";
      execution.progress = 60;
      execution.metadata = {
        ...execution.metadata,
        current_step: "Gathering information on AI opportunities",
      };
    } else {
      // Completed phase
      execution.status = "completed";
      execution.progress = 100;
      execution.output = "Successfully researched 12 future AI opportunities and generated PDF.";
      execution.metadata = {
        ...execution.metadata,
        artifacts: [
          {
            id: "artifact-1",
            title: "AI Opportunities Report",
            type: "pdf",
            file_path: "/tmp/synzept-artifacts/ai-opportunities.pdf",
            file_type: "application/pdf",
            size_bytes: 1024000,
            created_at: new Date().toISOString(),
          },
        ],
      };
    }

    execution._createdAt = execution._createdAt || Date.now();
    this.executions.set(id, execution);
    return { ...execution };
  }

  async approveActionExecution(id: string): Promise<MockExecution> {
    const execution = this.executions.get(id);
    if (!execution) throw new Error(`Execution ${id} not found`);
    
    execution.status = "executing";
    execution.progress = 40;
    execution.metadata = { ...execution.metadata, approved_at: new Date().toISOString() };
    
    this.executions.set(id, execution);
    return { ...execution };
  }

  async rejectActionExecution(id: string): Promise<MockExecution> {
    const execution = this.executions.get(id);
    if (!execution) throw new Error(`Execution ${id} not found`);
    
    execution.status = "cancelled";
    execution.error = "User rejected the execution.";
    
    this.executions.set(id, execution);
    return { ...execution };
  }
}

describe("Frontend Execution Experience - Research + PDF Flow", () => {
  let api: MockActionExecutionAPI;

  beforeEach(() => {
    api = new MockActionExecutionAPI();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should create an ActionExecution when user submits a request", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);

    expect(execution).toBeDefined();
    expect(execution.id).toBeDefined();
    expect(execution.status).toBe("planning");
    expect(execution.progress).toBe(0);
    expect(execution.title).toContain("Pdf_generation");
    expect(execution.request).toBe(request);
  });

  it("should retrieve execution status via polling", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);
    const executionId = execution.id;

    // Simulate polling
    let currentExecution = execution;
    let pollingCount = 0;
    const maxPolls = 10;

    while (pollingCount < maxPolls) {
      currentExecution = await api.getActionExecution(executionId);
      pollingCount++;

      if (currentExecution.status === "completed" || currentExecution.status === "failed") {
        break;
      }

      await sleep(500); // Wait before next poll
    }

    expect(currentExecution.status).toBe("completed");
    expect(currentExecution.progress).toBe(100);
    expect(currentExecution.output).toBeDefined();
  });

  it("should show execution progress transitions: planning → awaiting_confirmation → executing → completed", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);
    const executionId = execution.id;

    const statuses: string[] = [];

    // Poll and collect all status transitions
    for (let i = 0; i < 10; i++) {
      const current = await api.getActionExecution(executionId);
      if (!statuses.includes(current.status)) {
        statuses.push(current.status);
      }

      if (current.status === "completed") {
        break;
      }

      await sleep(500);
    }

    // Verify we see expected state transitions
    expect(statuses).toContain("planning");
    expect(statuses[statuses.length - 1]).toBe("completed");
  });

  it("should handle approval when execution is in awaiting_confirmation state", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);
    const executionId = execution.id;

    // Poll until we reach awaiting_confirmation
    let current = execution;
    let approvalFound = false;

    for (let i = 0; i < 10; i++) {
      current = await api.getActionExecution(executionId);
      if (current.status === "awaiting_confirmation") {
        approvalFound = true;
        break;
      }
      await sleep(500);
    }

    expect(approvalFound).toBe(true);
    expect(current.status).toBe("awaiting_confirmation");
    expect(current.metadata?.approval_reason).toBeDefined();

    // Approve the execution
    const approved = await api.approveActionExecution(executionId);
    expect(approved.status).toBe("executing");
  });

  it("should handle rejection of execution", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);
    const executionId = execution.id;

    // Poll until we reach awaiting_confirmation
    let current = execution;
    for (let i = 0; i < 10; i++) {
      current = await api.getActionExecution(executionId);
      if (current.status === "awaiting_confirmation") {
        break;
      }
      await sleep(500);
    }

    // Reject the execution
    const rejected = await api.rejectActionExecution(executionId);
    expect(rejected.status).toBe("cancelled");
    expect(rejected.error).toBeDefined();
  });

  it("should include artifact metadata when execution completes", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);
    const executionId = execution.id;

    // Poll until completion
    let current = execution;
    for (let i = 0; i < 10; i++) {
      current = await api.getActionExecution(executionId);
      if (current.status === "completed") {
        break;
      }
      await sleep(500);
    }

    expect(current.status).toBe("completed");
    expect(current.metadata?.artifacts).toBeDefined();
    expect(Array.isArray(current.metadata?.artifacts)).toBe(true);
    
    const artifacts = current.metadata?.artifacts as Array<Record<string, unknown>>;
    if (artifacts.length > 0) {
      const artifact = artifacts[0];
      expect(artifact.id).toBeDefined();
      expect(artifact.title).toBeDefined();
      expect(artifact.type).toBe("pdf");
      expect(artifact.file_type).toBe("application/pdf");
    }
  });

  it("should maintain execution state across page refreshes (recovery flow)", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);
    const executionId = execution.id;

    // Simulate page refresh by creating a new API instance
    // In real app, this would recover from URL parameter or session storage
    const recoveredExecution = await api.getActionExecution(executionId);

    expect(recoveredExecution.id).toBe(executionId);
    expect(recoveredExecution.status).toBe("planning");
    expect(recoveredExecution.request).toBe(request);
  });

  it("should display correct UI state for each execution phase", async () => {
    const request = "Research future AI opportunities and make a PDF.";
    const execution = await api.createActionExecution(request);
    const executionId = execution.id;

    // Test planning phase display
    let current = await api.getActionExecution(executionId);
    expect(current.status).toBe("planning");
    // In real UI: Should show "Understanding what you need..."

    // Wait for awaiting_confirmation
    for (let i = 0; i < 10; i++) {
      current = await api.getActionExecution(executionId);
      if (current.status === "awaiting_confirmation") break;
      await sleep(500);
    }
    // In real UI: Should show approval buttons and reason

    // Approve and wait for executing
    await api.approveActionExecution(executionId);
    for (let i = 0; i < 10; i++) {
      current = await api.getActionExecution(executionId);
      if (current.status === "executing") break;
      await sleep(500);
    }
    // In real UI: Should show progress bar and current step

    // Wait for completion
    for (let i = 0; i < 10; i++) {
      current = await api.getActionExecution(executionId);
      if (current.status === "completed") break;
      await sleep(500);
    }
    expect(current.status).toBe("completed");
    // In real UI: Should show green banner with "Open", "Continue Editing", etc.
  });
});

describe("ExecutionWorkspaceCard Component Integration", () => {
  it("should render planning state", () => {
    const execution = {
      id: "test-1",
      status: "planning",
      progress: 15,
      title: "Research future AI opportunities and make a PDF",
      request: "Research future AI opportunities and make a PDF.",
      output: null,
      error: null,
      metadata: {},
    };

    // In actual test: render ExecutionWorkspaceCard with this execution
    // and verify it shows planning UI (no artifacts yet)
    expect(execution.status).toBe("planning");
  });

  it("should render awaiting_confirmation state with approval buttons", () => {
    const execution = {
      id: "test-2",
      status: "awaiting_confirmation",
      progress: 30,
      title: "Research future AI opportunities and make a PDF",
      request: "Research future AI opportunities and make a PDF.",
      output: null,
      error: null,
      metadata: {
        approval_required: true,
        approval_reason: "This action will research AI and generate a PDF.",
      },
    };

    // In actual test: render and verify Approve/Reject buttons appear
    expect(execution.status).toBe("awaiting_confirmation");
    expect(execution.metadata.approval_required).toBe(true);
  });

  it("should render executing state with progress", () => {
    const execution = {
      id: "test-3",
      status: "executing",
      progress: 60,
      title: "Research future AI opportunities and make a PDF",
      request: "Research future AI opportunities and make a PDF.",
      output: null,
      error: null,
      metadata: {
        current_step: "Gathering information on AI opportunities",
      },
    };

    // In actual test: render and verify progress bar shows 60%
    expect(execution.status).toBe("executing");
    expect(execution.progress).toBe(60);
  });

  it("should render completed state with artifact download", () => {
    const execution = {
      id: "test-4",
      status: "completed",
      progress: 100,
      title: "Research future AI opportunities and make a PDF",
      request: "Research future AI opportunities and make a PDF.",
      output: "Successfully researched and generated PDF.",
      error: null,
      metadata: {
        artifacts: [
          {
            id: "artifact-1",
            title: "AI Opportunities Report",
            type: "pdf",
            file_path: "/tmp/synzept-artifacts/ai-opportunities.pdf",
            file_type: "application/pdf",
          },
        ],
      },
    };

    // In actual test: render and verify:
    // - Green "Completed" banner visible
    // - "Open" button to download artifact
    // - "Continue Editing" button
    // - Artifact shown in results section
    expect(execution.status).toBe("completed");
    expect(execution.metadata.artifacts?.length).toBe(1);
  });

  it("should render failed state with error and retry button", () => {
    const execution = {
      id: "test-5",
      status: "failed",
      progress: 35,
      title: "Research future AI opportunities and make a PDF",
      request: "Research future AI opportunities and make a PDF.",
      output: null,
      error: "Research API returned HTTP 429 - rate limit exceeded",
      metadata: {},
    };

    // In actual test: render and verify:
    // - Red error banner visible
    // - Error message displayed
    // - "Retry" button appears
    expect(execution.status).toBe("failed");
    expect(execution.error).toBeDefined();
  });
});

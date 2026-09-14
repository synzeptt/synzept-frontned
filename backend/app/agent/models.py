"""
Structured models for Agent execution plans and state.

These Pydantic models define the contract for how the Agent
orchestrator works with tools and execution plans.
"""

from datetime import datetime
from typing import Any, Optional
from enum import Enum
import uuid

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """Status of an agent execution."""
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolInputSchema(BaseModel):
    """JSON schema for tool input validation."""
    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class ToolOutputSchema(BaseModel):
    """JSON schema for tool output."""
    type: str = "object"
    properties: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(BaseModel):
    """Definition of a tool that the agent can use."""
    name: str
    description: str
    input_schema: ToolInputSchema
    output_schema: ToolOutputSchema
    category: str = "utility"  # e.g., "utility", "data", "file", "communication"


class AgentStepInput(BaseModel):
    """Input parameters for an agent step."""
    tool_name: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class AgentStep(BaseModel):
    """A single step in an agent execution plan."""
    id: str
    tool_name: str
    description: str
    input: AgentStepInput
    reason: str = "Execute this step as part of the plan"
    depends_on: list[str] = Field(default_factory=list)  # Step IDs this depends on
    retry_on_failure: bool = True
    max_retries: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"


class AgentPlan(BaseModel):
    """Structured execution plan for an agent request."""
    goal: str
    description: str = ""
    steps: list[AgentStep]
    verification_requirements: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)  # Additional context for the plan


class ToolExecutionResult(BaseModel):
    """Result from executing a tool."""
    tool_name: str
    step_id: str
    success: bool
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[str] = None
    execution_time_seconds: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentStepExecution(BaseModel):
    """Execution record for a single agent step."""
    id: str
    step_id: str
    tool_name: str
    status: ExecutionStatus
    input: AgentStepInput
    result: Optional[ToolExecutionResult] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    attempts: int = 0
    last_error: Optional[str] = None


class AgentExecution(BaseModel):
    """Complete execution state of an agent request."""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    request_message: str
    plan: Optional[AgentPlan] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step_index: int = 0
    steps: list[AgentStepExecution] = Field(default_factory=list)
    final_result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

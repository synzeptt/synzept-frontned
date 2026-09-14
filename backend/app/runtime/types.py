from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class ExecutionState(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_FOR_INFORMATION = "waiting_for_information"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    RETRYING = "retrying"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 1
    retry_delay_seconds: float = 0.0
    backoff_multiplier: float = 1.0


@dataclass(slots=True)
class ExecutionStep:
    id: str
    runner: str
    action: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    output: Any | None = None
    error: str | None = None
    attempts: int = 0


@dataclass(slots=True)
class ApprovalCheckpoint:
    required: bool = False
    granted: bool = False
    reason: str | None = None


@dataclass(slots=True)
class VerificationResult:
    passed: bool
    details: str | None = None
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionEvent:
    execution_id: str
    event_type: str
    state: ExecutionState
    timestamp: str
    step_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionContext:
    execution_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Execution:
    id: str
    goal: str
    steps: list[ExecutionStep] = field(default_factory=list)
    state: ExecutionState = ExecutionState.CREATED
    current_step_index: int = 0
    result: Any | None = None
    error: str | None = None
    verification: VerificationResult | None = None
    approval: ApprovalCheckpoint | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, *, goal: str, steps: list[ExecutionStep] | None = None) -> "Execution":
        return cls(id=str(uuid4()), goal=goal, steps=list(steps or []))


@dataclass(slots=True)
class ExecutionResult:
    execution_id: str
    state: ExecutionState
    output: Any | None = None
    error: str | None = None
    result: Any | None = None

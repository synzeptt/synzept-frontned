from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExecutionLifecycleState(str, Enum):
    PLANNING = "planning"
    CLARIFYING = "clarifying"
    EXECUTING = "executing"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    RESUMING = "resuming"
    GENERATING_ARTIFACTS = "generating_artifacts"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class ExecutionStateRecord:
    state: ExecutionLifecycleState
    metadata: dict[str, Any] = field(default_factory=dict)


class ExecutionStateMachine:
    """Tracks lifecycle transitions for an execution."""

    def __init__(self) -> None:
        self.history: list[ExecutionStateRecord] = []

    def transition(self, *, state: ExecutionLifecycleState, metadata: dict[str, Any] | None = None) -> ExecutionStateRecord:
        record = ExecutionStateRecord(state=state, metadata=metadata or {})
        self.history.append(record)
        return record

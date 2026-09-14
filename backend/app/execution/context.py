from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SharedExecutionContext:
    goal: str
    execution_id: str | None = None
    execution_memory: dict[str, Any] = field(default_factory=dict)
    planner_output: dict[str, Any] | None = None
    clarification_answers: dict[str, Any] = field(default_factory=dict)
    progress: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    approval_status: str = "not_required"
    current_worker: str | None = None
    current_step: str | None = None
    worker_plan: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

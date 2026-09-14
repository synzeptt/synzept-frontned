from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class PlanStep:
    id: str
    title: str
    status: str = "pending"
    estimated_minutes: int = 1
    tools: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    expected_output: str = ""
    requires_approval: bool = False
    worker_id: str | None = None
    worker_name: str | None = None
    worker_capabilities: list[str] = field(default_factory=list)
    worker_requires_approval: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    skill_id: str | None = None
    skill_name: str | None = None


@dataclass(slots=True)
class ExecutionPlan:
    objective: str
    intent: str
    estimated_minutes: int
    tools: list[str]
    dependencies: list[str]
    expected_outputs: list[str]
    requires_approval: bool
    approval_reason: str | None
    context: dict[str, Any]
    steps: list[PlanStep]
    intent_analysis: dict[str, Any] = field(default_factory=dict)
    skills: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

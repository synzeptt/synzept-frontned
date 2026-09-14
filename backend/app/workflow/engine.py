from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.execution.engine import ExecutionContext, ExecutionStep


@dataclass(slots=True)
class WorkflowStep:
    id: str
    runner: str
    action: str
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


class WorkflowEngine:
    def __init__(self, registry: dict[str, Any] | None = None) -> None:
        self.registry = registry or {}

    async def run(self, workflow: list[WorkflowStep], *, context: ExecutionContext) -> dict[str, Any]:
        steps_output: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []
        for step in workflow:
            step.status = "running"
            runner = self.registry.get(step.runner)
            if runner is None:
                step.status = "failed"
                steps_output.append({"id": step.id, "status": step.status, "error": f"unknown runner: {step.runner}"})
                break
            result = await runner.execute(step=ExecutionStep(id=step.id, runner=step.runner, action=step.action, metadata=step.metadata), context=context)
            step.status = result.get("status", "completed")
            steps_output.append({"id": step.id, "status": step.status, "output": result.get("output")})
            if result.get("artifacts"):
                artifacts.extend([{"title": artifact.title, "type": artifact.artifact_type} for artifact in result.get("artifacts", [])])
        return {
            "status": "completed" if all(item["status"] == "completed" for item in steps_output) else "failed",
            "steps": steps_output,
            "artifacts": artifacts,
            "metadata": {"artifacts_passed": 1 if artifacts else 1},
        }

from __future__ import annotations

from typing import Any

from app.execution.engine import ExecutionContext, ExecutionStep, StepExecutor
from app.skills.context import SkillContext
from app.skills.registry import default_registry
from app.skills.result import ExecutionMetrics, SkillExecutionStatus, SkillResult


class SkillStepExecutor(StepExecutor):
    """Run an existing domain runner through the complete Skill lifecycle."""

    def __init__(self, skill_name: str | None, delegate: StepExecutor) -> None:
        self.name = skill_name or getattr(delegate, "name", "skill")
        self.skill_name = skill_name
        self.delegate = delegate

    async def execute(self, *, step: ExecutionStep, context: ExecutionContext) -> dict[str, Any]:
        skill_name = str(step.metadata.get("skill") or self.skill_name or "")
        skill_class = default_registry.get_skill_class(skill_name)
        if skill_class is None:
            return {"status": "failed", "error": f"unknown skill: {skill_name}"}

        skill_context = SkillContext(
            execution_id=context.session.id,
            intent=step.action,
            goal=context.session.goal,
            planner_output={**(step.metadata.get("plan_step") or {}), "capability": skill_name},
            runtime_context={"goal": context.session.goal, "timeline": [], "artifacts": []},
        )
        understanding = skill_class().understand(skill_context)
        skill = skill_class()
        skill_context.runtime_context["understanding"] = understanding
        skill_context.runtime_context["plan"] = skill.plan(skill_context).planned_steps
        skill.prepare(skill_context)
        skill_execution = skill.execute(skill_context)

        delegated = await self.delegate.execute(step=step, context=context)
        if delegated.get("status") not in {None, "completed"}:
            return delegated

        artifacts = _normalize_artifacts(delegated.get("artifacts") or [])
        skill_context.runtime_context["artifacts"] = artifacts
        skill_context.runtime_context.setdefault("timeline", []).append({"phase": "completed", "label": f"{skill_name} completed"})
        skill_context.runtime_context["result"] = delegated.get("result") or delegated.get("output")
        delegated_result = delegated.get("result")
        if isinstance(delegated_result, dict) and delegated_result.get("report"):
            skill_context.runtime_context["report"] = delegated_result["report"]
        skill_result = SkillResult(
            status=SkillExecutionStatus.SUCCESS,
            outputs={
                "artifacts": artifacts or skill_execution.outputs.get("artifacts", []),
                "result": skill_context.runtime_context["result"],
            },
            message=delegated.get("output") if isinstance(delegated.get("output"), str) else None,
            metrics=ExecutionMetrics(),
        )
        skill_result.metrics.finish()
        verification = skill.verify(skill_context)
        if not verification.passed:
            return {
                **delegated,
                "status": "failed",
                "error": verification.message or f"{skill_name} verification failed",
                "verification": {"verified": False, "evidence": verification.evidence, "message": verification.message},
            }

        delivered = skill.deliver(skill_context, skill_result)
        learning = skill.learn(skill_context, skill_result)
        return {
            **delegated,
            "status": "completed",
            "artifacts": _normalize_artifacts(delivered or artifacts),
            "verification": {
                "verified": True,
                "evidence": verification.evidence,
                "message": verification.message or f"{skill_name} verified",
            },
            "metadata": {
                **(delegated.get("metadata") or {}),
                "skill": skill_name,
                "understanding": understanding,
                "skill_plan": skill_context.runtime_context["plan"],
                "learning": learning,
            },
        }


def register_skill_runner(registry: Any, runner_name: str, skill_name: str | None, delegate: StepExecutor) -> None:
    """Register a runner under its domain skill without exposing implementation details to planning."""
    registry.register(runner_name, SkillStepExecutor(skill_name, delegate))


def _normalize_artifacts(artifacts: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for artifact in artifacts:
        if isinstance(artifact, dict):
            normalized.append(artifact)
        elif hasattr(artifact, "title"):
            normalized.append({
                "name": artifact.title,
                "title": artifact.title,
                "content": getattr(artifact, "content", None),
                "artifact_type": getattr(artifact, "artifact_type", "result"),
            })
    return normalized
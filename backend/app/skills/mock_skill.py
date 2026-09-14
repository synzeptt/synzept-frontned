from typing import Any, Dict, List
from .base import Skill
from .context import SkillContext
from .result import PlanningResult, SkillResult, DeliverableReference, VerificationResult, SkillExecutionStatus
from .registry import default_registry


@default_registry.autoregister("mock-skill")
class MockSkill(Skill):
    identity = "mock-skill"
    purpose = "validate the skill framework and worker orchestration"
    capabilities = ["mock-skill"]

    def plan(self, context: SkillContext) -> PlanningResult:
        # produce a single step that asks for the mock worker
        steps = [{"capability": "mock", "inputs": context.planner_output.get("inputs", {})}]
        return PlanningResult(planned_steps=steps, estimated_cost=0.0, estimated_duration=0.0)

    def prepare(self, context: SkillContext) -> None:
        context.logger.info("MockSkill.prepare")

    def execute(self, context: SkillContext) -> SkillResult:
        # orchestration is done by SkillManager; here we only return after orchestration
        return SkillResult(status=SkillExecutionStatus.SUCCESS, outputs={}, message="executed")

    def verify(self, context: SkillContext) -> VerificationResult:
        # Simple pass-through verification
        return VerificationResult(passed=True, evidence={"mock": True})

    def cleanup(self, context: SkillContext) -> None:
        context.logger.info("MockSkill.cleanup")

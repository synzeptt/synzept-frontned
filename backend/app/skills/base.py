from abc import ABC, abstractmethod
from typing import Any

from .context import SkillContext
from .result import SkillResult, PlanningResult


class Skill(ABC):
    """Base Skill contract.

    Skills implement planning, preparation, execution orchestration and verification.
    """

    identity: str = ""
    purpose: str = ""
    capabilities: list = []

    def __init__(self, **dependencies: Any):
        self.deps = dependencies

    def understand(self, context: SkillContext) -> dict[str, Any]:
        """Normalize the user outcome before planning implementation steps."""
        return {
            "skill": self.identity,
            "goal": context.goal,
            "intent": context.intent or context.goal,
            "constraints": context.planner_output.get("constraints", {}),
        }

    @abstractmethod
    def plan(self, context: SkillContext) -> PlanningResult:
        raise NotImplementedError()

    @abstractmethod
    def prepare(self, context: SkillContext) -> None:
        raise NotImplementedError()

    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        raise NotImplementedError()

    @abstractmethod
    def verify(self, context: SkillContext) -> "VerificationResult":
        raise NotImplementedError()

    @abstractmethod
    def cleanup(self, context: SkillContext) -> None:
        raise NotImplementedError()

    def deliver(self, context: SkillContext, result: SkillResult) -> list[dict[str, Any]]:
        """Return structured artifacts for the Work surface."""
        return [item for item in result.outputs.get("artifacts", []) if isinstance(item, dict)]

    def learn(self, context: SkillContext, result: SkillResult) -> dict[str, Any]:
        """Return an execution signal consumed by the learning layer."""
        return {
            "skill": self.identity,
            "status": result.status.value,
            "duration": result.metrics.duration,
            "goal": context.goal,
        }

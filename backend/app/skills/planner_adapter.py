import uuid
from typing import Any, Dict

from .context import SkillContext
from .registry import default_registry
from ..workers.manager import WorkerManager


class PlannerAdapter:
    """Translate planner output into SkillContext and instantiate Skill.

    Planner output is expected to include a `capability` field and optional `inputs`.
    """

    def __init__(self, registry=default_registry, worker_manager: WorkerManager = None):
        self.registry = registry
        self.worker_manager = worker_manager or WorkerManager()

    def build_context(self, planner_output: Dict[str, Any]) -> SkillContext:
        capability = planner_output.get("capability")
        if not capability:
            raise ValueError("planner_output missing capability")
        exec_id = planner_output.get("execution_id") or str(uuid.uuid4())
        context = SkillContext(
            execution_id=exec_id,
            intent=planner_output.get("intent", ""),
            goal=planner_output.get("goal", ""),
            planner_output=planner_output,
            worker_manager=self.worker_manager,
        )
        return context

    def get_skill_class(self, planner_output: Dict[str, Any]):
        capability = planner_output.get("capability")
        cls = self.registry.get_skill_class(capability)
        if cls is None:
            raise KeyError(f"Skill not found for capability: {capability}")
        return cls

    def build_skill(self, planner_output: Dict[str, Any]):
        cls = self.get_skill_class(planner_output)
        context = self.build_context(planner_output)
        return cls(), context

from typing import Any, Dict, List
import uuid
import logging

from .registry import default_registry
from .planner_adapter import PlannerAdapter
from .manager import SkillManager
from .context import SkillContext
from .result import SkillResult, SkillExecutionStatus
from ..events import default_event_bus


class SkillRuntimeAdapter:
    def __init__(self, registry=default_registry, worker_manager=None, event_bus=None):
        self.registry = registry
        self.planner = PlannerAdapter(registry=registry, worker_manager=worker_manager)
        self.manager = SkillManager(registry=registry, dependencies={})
        self.events = event_bus or default_event_bus
        self._persistence: List[Dict[str, Any]] = []

    def execute_from_planner(self, planner_output: Dict[str, Any]) -> SkillResult:
        exec_id = planner_output.get("execution_id") or str(uuid.uuid4())
        planner_output["execution_id"] = exec_id
        self.events.emit("execution.created", {"execution_id": exec_id, "goal": planner_output.get("goal")})
        self.events.emit("planning.started", {"execution_id": exec_id})
        skill_instance, context = self.planner.build_skill(planner_output)
        self.events.emit("planning.completed", {"execution_id": exec_id, "skill": getattr(skill_instance, "identity", None)})
        # instantiate via manager if needed (planner already returns an instance)
        self.events.emit("skill.started", {"execution_id": exec_id, "skill": getattr(skill_instance, "identity", None)})
        # run
        result = self.manager.run(skill_instance, context)
        # verification events are emitted by manager/worker layers; mark verification outcome
        self.events.emit("verification.started", {"execution_id": exec_id})
        if result.status == SkillExecutionStatus.SUCCESS:
            self.events.emit("verification.passed", {"execution_id": exec_id})
        else:
            self.events.emit("verification.failed", {"execution_id": exec_id})
        # persist
        record = {"execution_id": exec_id, "goal": planner_output.get("goal"), "result": result}
        self._persistence.append(record)
        ev = "execution.completed" if result.status == SkillExecutionStatus.SUCCESS else "execution.failed"
        self.events.emit(ev, {"execution_id": exec_id, "result": result})
        return result

    def get_persisted(self) -> List[Dict[str, Any]]:
        return list(self._persistence)

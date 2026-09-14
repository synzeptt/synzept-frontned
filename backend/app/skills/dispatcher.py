from __future__ import annotations

from typing import Any

from app.events import default_event_bus

from .manager import SkillManager
from .result import SkillExecutionStatus, SkillResult
from .router import SkillRouter


class SkillDispatcher:
    """Execute a planner output through the registered skill lifecycle."""

    def __init__(self, router: SkillRouter | None = None, manager: SkillManager | None = None):
        self.router = router or SkillRouter()
        self.manager = manager or SkillManager()

    def dispatch(self, planner_output: dict[str, Any]) -> SkillResult:
        skill_cls, context = self.router.resolve(planner_output)
        skill_instance = self.manager.instantiate(skill_cls)

        default_event_bus.emit("skill.understood", {"execution_id": context.execution_id, "skill": getattr(skill_instance, "identity", skill_cls.__name__)})
        default_event_bus.emit("planning.started", {"execution_id": context.execution_id, "skill": getattr(skill_instance, "identity", skill_cls.__name__)})
        default_event_bus.emit("planning.completed", {"execution_id": context.execution_id, "skill": getattr(skill_instance, "identity", skill_cls.__name__)})
        default_event_bus.emit("skill.started", {"execution_id": context.execution_id, "skill": getattr(skill_instance, "identity", skill_cls.__name__)})

        result = self.manager.run(skill_instance, context)
        status = "success" if result.status == SkillExecutionStatus.SUCCESS else "failure"
        default_event_bus.emit("execution.completed" if status == "success" else "execution.failed", {"execution_id": context.execution_id, "skill": getattr(skill_instance, "identity", skill_cls.__name__), "result": result})
        return result

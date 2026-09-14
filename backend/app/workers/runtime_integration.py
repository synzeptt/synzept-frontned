from typing import Any, Callable, Dict, List
import uuid
import logging

from .registry import default_registry
from .manager import WorkerManager
from .context import WorkerContext
from .result import WorkerResult
from ..events import default_event_bus


class RuntimeAdapter:
    """Lightweight adapter the runtime can call to execute workers."""

    def __init__(self, registry=default_registry, dependencies: Dict[str, Any] = None, event_bus=None):
        self.registry = registry
        self.manager = WorkerManager(registry=registry, dependencies=dependencies or {}, event_bus=event_bus)
        self.events = event_bus or default_event_bus
        self._persistence: List[Dict[str, Any]] = []

    def execute(self, capability: str, goal: str, inputs: Dict[str, Any]) -> WorkerResult:
        exec_id = str(uuid.uuid4())
        context = WorkerContext(execution_id=exec_id, goal=goal, inputs=inputs)
        self.events.emit("execution.created", {"execution_id": exec_id, "goal": goal})
        result = self.manager.run(capability, context)
        # persist minimal outcome
        record = {"execution_id": exec_id, "goal": goal, "result": result}
        self._persistence.append(record)
        # emit events for success/failure
        ev = "execution.completed" if result.status.name == "SUCCESS" else "execution.failed"
        self.events.emit(ev, {"execution_id": exec_id, "result": result})
        return result

    def get_persisted(self) -> List[Dict[str, Any]]:
        return list(self._persistence)

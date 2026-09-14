from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging
import threading

from ..workers.manager import WorkerManager


@dataclass
class SkillContext:
    execution_id: str
    intent: str
    goal: str
    planner_output: Dict[str, Any] = field(default_factory=dict)
    runtime_context: Dict[str, Any] = field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    connectors: Dict[str, Any] = field(default_factory=dict)
    worker_manager: WorkerManager = field(default_factory=WorkerManager)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("skill"))
    cancellation_token: threading.Event = field(default_factory=threading.Event)

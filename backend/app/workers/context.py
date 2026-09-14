from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging
import threading


@dataclass
class WorkerContext:
    execution_id: str
    goal: str
    current_step: Optional[str] = None
    runtime_context: Dict[str, Any] = field(default_factory=dict)
    inputs: Dict[str, Any] = field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    connectors: Dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("worker"))
    cancellation_token: threading.Event = field(default_factory=threading.Event)


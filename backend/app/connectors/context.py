from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import logging
import threading


@dataclass(frozen=True)
class ConnectorContext:
    execution_id: str
    skill_id: Optional[str]
    worker_id: Optional[str]
    auth: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("connector"))
    cancellation_token: threading.Event = field(default_factory=threading.Event)

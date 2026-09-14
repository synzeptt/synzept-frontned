from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .types import ExecutionEvent, ExecutionState


def build_event(execution_id: str, event_type: str, state: ExecutionState, *, step_id: str | None = None, metadata: dict[str, Any] | None = None) -> ExecutionEvent:
    return ExecutionEvent(
        execution_id=execution_id,
        event_type=event_type,
        state=state,
        timestamp=datetime.now(timezone.utc).isoformat(),
        step_id=step_id,
        metadata=metadata or {},
    )

__all__ = ["build_event"]

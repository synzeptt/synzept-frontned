from __future__ import annotations

from .types import ExecutionContext


def make_context(execution_id: str, *, metadata: dict | None = None) -> ExecutionContext:
    return ExecutionContext(execution_id=execution_id, metadata=metadata or {})

__all__ = ["make_context"]

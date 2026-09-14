from __future__ import annotations

import asyncio
from typing import Any


class ExecutionLearningStore:
    """Stores compact operational knowledge derived from completed executions."""

    def __init__(self, backend: Any | None = None) -> None:
        self.backend = backend

    async def record(self, *, user_id: Any, knowledge: dict[str, Any], **_: Any) -> None:
        if self.backend is None:
            return
        if hasattr(self.backend, "create"):
            await self.backend.create(user_id=user_id, content=str(knowledge), category="execution_learning", memory_type="project", importance=0.8)
            return
        if hasattr(self.backend, "append"):
            await self.backend.append(knowledge)

    async def list(self, *, user_id: Any, goal: str, intent: str | None = None, capabilities: list[str] | None = None, limit: int = 5, **_: Any) -> list[dict[str, Any]]:
        if self.backend is None:
            return []
        if hasattr(self.backend, "list"):
            records = await self.backend.list(user_id=user_id, goal=goal, intent=intent, capabilities=capabilities, limit=limit)
            if records:
                return records
        return []

    async def summarize(self, *, user_id: Any, goal: str, **_: Any) -> dict[str, Any]:
        records = await self.list(user_id=user_id, goal=goal, limit=5)
        if not records:
            return {}
        return {"records": records, "count": len(records)}

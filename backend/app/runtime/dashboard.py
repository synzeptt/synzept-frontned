from __future__ import annotations

from typing import Any

from .metrics import ExecutionMetricsStore


class ExecutionDashboardService:
    def __init__(self, metrics_store: ExecutionMetricsStore | None = None) -> None:
        self.metrics_store = metrics_store or ExecutionMetricsStore()

    def list(self) -> list[dict[str, Any]]:
        return self.metrics_store.list()

    def summary(self) -> dict[str, Any]:
        records = self.metrics_store.list()
        return {
            "total": len(records),
            "completed": sum(1 for item in records if item.get("success") is True),
            "failed": sum(1 for item in records if item.get("success") is False),
            "waiting_for_approval": sum(1 for item in records if item.get("waiting_for_approval") is True),
            "artifacts_generated": sum(int(item.get("artifacts_generated", 0)) for item in records),
        }

from __future__ import annotations

import time
from typing import Dict


class MetricsCollector:
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._timings: Dict[str, float] = {}

    def incr(self, key: str, amount: int = 1) -> None:
        self._counters[key] = self._counters.get(key, 0) + amount

    def timing(self, key: str, seconds: float) -> None:
        self._timings[key] = self._timings.get(key, 0.0) + seconds

    def snapshot(self) -> Dict[str, Dict]:
        return {"counters": dict(self._counters), "timings": dict(self._timings)}


default_metrics = MetricsCollector()

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExecutionMetrics:
    duration_seconds: float = 0.0
    retries: int = 0
    attempts: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)

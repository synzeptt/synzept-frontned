"""Lightweight V1 monitoring primitives.

This is intentionally in-process: enough signal for production readiness without
introducing an external observability platform.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Iterator


@dataclass(slots=True)
class MetricEvent:
    name: str
    duration_ms: int
    status: str
    tags: dict
    timestamp: float


class PerformanceMonitor:
    def __init__(self, max_events: int = 500) -> None:
        self._events: deque[MetricEvent] = deque(maxlen=max_events)
        self._counts: dict[str, int] = defaultdict(int)
        self._lock = Lock()

    def record(self, name: str, duration_ms: int, status: str = "success", **tags) -> None:
        event = MetricEvent(name=name, duration_ms=duration_ms, status=status, tags=tags, timestamp=time.time())
        with self._lock:
            self._events.append(event)
            self._counts[f"{name}:{status}"] += 1

    @contextmanager
    def timed(self, name: str, **tags) -> Iterator[None]:
        start = time.perf_counter()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            self.record(name, int((time.perf_counter() - start) * 1000), status, **tags)

    def snapshot(self) -> dict:
        with self._lock:
            events = list(self._events)
            counts = dict(self._counts)
        by_name: dict[str, list[int]] = defaultdict(list)
        slowest: list[dict] = []
        for event in events:
            by_name[event.name].append(event.duration_ms)
            slowest.append(
                {
                    "name": event.name,
                    "duration_ms": event.duration_ms,
                    "status": event.status,
                    "tags": event.tags,
                    "timestamp": event.timestamp,
                }
            )
        aggregates = {}
        for name, durations in by_name.items():
            ordered = sorted(durations)
            aggregates[name] = {
                "count": len(durations),
                "avg_ms": int(sum(durations) / len(durations)),
                "p95_ms": ordered[max(0, int(len(ordered) * 0.95) - 1)],
                "max_ms": ordered[-1],
            }
        return {
            "counts": counts,
            "aggregates": aggregates,
            "slowest": sorted(slowest, key=lambda item: item["duration_ms"], reverse=True)[:10],
        }


monitor = PerformanceMonitor()

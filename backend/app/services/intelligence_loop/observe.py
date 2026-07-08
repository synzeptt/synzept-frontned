from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.intelligence_loop import IntelligenceEventOut
from app.services.intelligence_loop.mock_data import MOCK_RAW_EVENTS


class ObserveService:
    def __init__(self, raw_events: list[dict[str, Any]] | None = None) -> None:
        self.raw_events = deepcopy(raw_events or MOCK_RAW_EVENTS)

    def collect_events(self) -> list[IntelligenceEventOut]:
        return [self.normalize_event(event) for event in self.raw_events]

    @staticmethod
    def normalize_event(event: dict[str, Any]) -> IntelligenceEventOut:
        return IntelligenceEventOut(
            id=event["id"],
            source=event["source"],
            eventType=event["eventType"],
            title=event["title"],
            description=event["description"],
            occurredAt=event["occurredAt"],
            actor=event.get("actor", "system"),
            entities=list(event.get("entities", [])),
            signals=list(event.get("signals", [])),
            importance=event.get("importance", 50),
            urgency=event.get("urgency", 50),
            metadata=dict(event.get("metadata", {})),
        )

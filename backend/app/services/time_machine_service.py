from __future__ import annotations

from app.schemas.time_machine import (
    TimeMachineComparisonOut,
    TimeMachineReflectionOut,
    TimeMachineSearchResultOut,
    TimeMachineTimelineEntryOut,
    TimeMachineTurningPointOut,
)
from app.services.time_machine_mock_data import (
    MOCK_COMPARISONS,
    MOCK_REFLECTIONS,
    MOCK_SEARCH_RESULTS,
    MOCK_TIMELINE_EVENTS,
    MOCK_TURNING_POINTS,
)


class TimeMachineService:
    def __init__(self) -> None:
        self.timeline_events = MOCK_TIMELINE_EVENTS
        self.turning_points = MOCK_TURNING_POINTS
        self.reflections = MOCK_REFLECTIONS
        self.comparisons = MOCK_COMPARISONS
        self.search_results = MOCK_SEARCH_RESULTS

    def journey(self, kind: str | None = None, query: str = "") -> list[TimeMachineTimelineEntryOut]:
        items = self.timeline_events
        if kind:
            items = [entry for entry in items if entry["kind"] == kind]
        if query:
            needle = query.lower()
            items = [entry for entry in items if needle in entry["title"].lower() or needle in entry["summary"].lower() or needle in " ".join(entry["tags"]).lower()]
        return [TimeMachineTimelineEntryOut(**entry) for entry in items]

    def turning_points(self) -> list[TimeMachineTurningPointOut]:
        return [TimeMachineTurningPointOut(**entry) for entry in self.turning_points]

    def reflections(self) -> list[TimeMachineReflectionOut]:
        return [TimeMachineReflectionOut(**entry) for entry in self.reflections]

    def compare(self) -> list[TimeMachineComparisonOut]:
        return [TimeMachineComparisonOut(**entry) for entry in self.comparisons]

    def search(self, query: str = "") -> list[TimeMachineSearchResultOut]:
        if not query:
            return [TimeMachineSearchResultOut(**entry) for entry in self.search_results]
        needle = query.lower()
        filtered = [entry for entry in self.search_results if needle in entry["title"].lower() or needle in entry["snippet"].lower()]
        return [TimeMachineSearchResultOut(**entry) for entry in filtered]

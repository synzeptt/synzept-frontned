from __future__ import annotations

from typing import Any
from uuid import UUID


class MemoryImprovementService:
    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def learn_from_execution(self, *, user_id: UUID, action_type: str, goal: str, summary: str, artifacts: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
        focus_areas = []
        if "pricing" in goal.casefold():
            focus_areas.append("pricing")
        if "project" in goal.casefold() or "roadmap" in goal.casefold():
            focus_areas.append("delivery")
        if summary:
            focus_areas.append("summary")
        recommendation = "Prioritize the strongest evidence first and keep notes connected to the latest project context." if focus_areas else "Continue capturing concise summaries after each completed workflow."
        memory = {
            "user_id": str(user_id),
            "project_memory": {"focus_areas": focus_areas, "last_goal": goal, "last_summary": summary[:220]},
            "decision_history": [{"action_type": action_type, "goal": goal, "summary": summary[:220]}],
            "preferences": {"focus_areas": focus_areas, "preferred_artifact_types": [artifact.get("type") for artifact in artifacts if artifact.get("type")]},
            "recommendations": [recommendation],
        }
        return {
            "memory": memory,
            "preferences": memory["preferences"],
            "recommendations": memory["recommendations"],
        }
        self._history.append(memory)
        return memory

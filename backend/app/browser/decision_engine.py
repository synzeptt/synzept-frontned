from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class LLMDecisionEngine:
    """A lightweight, auditable decision engine that produces structured browser decisions."""

    def __init__(self, llm_client: Any | None = None) -> None:
        self.llm_client = llm_client

    def decide(self, *, goal: str, observation: dict[str, Any], memory: dict[str, Any], previous_actions: list[dict[str, Any]], progress: dict[str, Any]) -> dict[str, Any]:
        current_understanding = self._summarize_observation(observation, goal)
        selected_action = self._select_action(goal, observation, memory, previous_actions, progress)
        confidence_score = self._confidence(goal, observation, memory, previous_actions)
        alternative_actions = self._alternative_actions(goal, observation)
        reasoning = self._build_reasoning(goal, observation, memory, selected_action, confidence_score)
        return {
            "current_understanding": current_understanding,
            "reasoning": reasoning,
            "selected_action": selected_action,
            "confidence_score": confidence_score,
            "alternative_actions": alternative_actions,
            "why_chosen": self._why_chosen(goal, observation, selected_action, confidence_score),
            "goal_achieved": self._goal_achieved(goal, observation),
            "requires_approval": self._requires_approval(goal, observation),
            "raw": {"goal": goal, "observation": observation, "memory": memory, "progress": progress},
        }

    def _summarize_observation(self, observation: dict[str, Any], goal: str) -> str:
        primary = observation.get("primary_action") or "Inspect page"
        buttons = ", ".join(str(item) for item in observation.get("buttons", [])[:4]) or "none"
        forms = ", ".join(str(item) for item in observation.get("forms", [])[:4]) or "none"
        return f"Goal: {goal}. Page shows a {primary.lower()} flow with buttons [{buttons}] and forms [{forms}]."

    def _select_action(self, goal: str, observation: dict[str, Any], memory: dict[str, Any], previous_actions: list[dict[str, Any]], progress: dict[str, Any]) -> str:
        if observation.get("error_messages"):
            return "recover"
        if observation.get("primary_action") == "Search":
            return "observe"
        if observation.get("semantic_roles", {}).get("primary") or observation.get("buttons"):
            return "observe"
        return "stop"

    def _confidence(self, goal: str, observation: dict[str, Any], memory: dict[str, Any], previous_actions: list[dict[str, Any]]) -> float:
        score = 0.65
        if observation.get("buttons"):
            score += 0.1
        if observation.get("forms"):
            score += 0.1
        if observation.get("main_content"):
            score += 0.08
        if memory.get("visited_urls"):
            score += 0.05
        if previous_actions:
            score += 0.02
        return min(score, 0.99)

    def _alternative_actions(self, goal: str, observation: dict[str, Any]) -> list[str]:
        alternative = []
        if observation.get("primary_action") == "Search":
            alternative.append("refresh")
        if observation.get("buttons"):
            alternative.append("inspect")
        alternative.append("stop")
        return alternative

    def _build_reasoning(self, goal: str, observation: dict[str, Any], memory: dict[str, Any], selected_action: str, confidence_score: float) -> str:
        return (
            f"The current page offers enough signals to continue toward '{goal}'. "
            f"The selected action '{selected_action}' has confidence {confidence_score:.2f} because the page exposes actionable UI elements and prior memory suggests progress is possible."
        )

    def _why_chosen(self, goal: str, observation: dict[str, Any], selected_action: str, confidence_score: float) -> str:
        return f"{selected_action} is the most direct next step because it aligns with the current objective and the page contains recognizable affordances."

    def _goal_achieved(self, goal: str, observation: dict[str, Any]) -> bool:
        return bool(observation.get("detected_results")) or bool(observation.get("main_content"))

    def _requires_approval(self, goal: str, observation: dict[str, Any]) -> bool:
        return "submit" in (goal or "").casefold() or bool(observation.get("dialogs"))

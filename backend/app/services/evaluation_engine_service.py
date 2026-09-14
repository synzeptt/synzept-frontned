from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_execution import ActionExecution


@dataclass(slots=True)
class ActionEvaluationResult:
    accuracy: float
    completeness: float
    reliability: float
    user_satisfaction: float
    efficiency: float
    overall_score: float
    confidence_level: str
    notes: list[str]


class ActionEvaluationService:
    """Evaluates completed actions before their outcomes are used for learning."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def evaluate(self, action: ActionExecution) -> ActionEvaluationResult:
        metadata = action.metadata_ or {}
        worker_result = (metadata.get("worker_result") or {}) if isinstance(metadata, dict) else {}
        tool_activity = metadata.get("tool_activity") or []
        feedback_signal = metadata.get("feedback_signal") or {}

        accuracy = self._accuracy_score(action, worker_result)
        completeness = self._completeness_score(action, worker_result)
        reliability = self._reliability_score(tool_activity)
        user_satisfaction = self._user_satisfaction_score(feedback_signal)
        efficiency = self._efficiency_score(worker_result, tool_activity)

        overall_score = round(
            (accuracy * 0.3 + completeness * 0.25 + reliability * 0.2 + user_satisfaction * 0.15 + efficiency * 0.1),
            3,
        )
        confidence_level = self._confidence_label(overall_score)
        notes = self._notes(action, overall_score, confidence_level)

        action.metadata_ = {
            **(action.metadata_ or {}),
            "evaluation": {
                "accuracy": round(accuracy, 3),
                "completeness": round(completeness, 3),
                "reliability": round(reliability, 3),
                "user_satisfaction": round(user_satisfaction, 3),
                "efficiency": round(efficiency, 3),
                "overall_score": overall_score,
                "confidence_level": confidence_level,
                "notes": notes,
            },
        }
        return ActionEvaluationResult(
            accuracy=accuracy,
            completeness=completeness,
            reliability=reliability,
            user_satisfaction=user_satisfaction,
            efficiency=efficiency,
            overall_score=overall_score,
            confidence_level=confidence_level,
            notes=notes,
        )

    def _accuracy_score(self, action: ActionExecution, worker_result: dict[str, Any]) -> float:
        score = 0.6
        if action.output:
            score += 0.2
        if worker_result.get("confidence_score"):
            score += min(0.15, worker_result.get("confidence_score", 0.0) * 0.15)
        if action.request and action.output and len(action.output.strip()) > 20:
            score += 0.05
        return min(0.99, round(score, 3))

    def _completeness_score(self, action: ActionExecution, worker_result: dict[str, Any]) -> float:
        score = 0.7
        if action.progress >= 100:
            score += 0.2
        if worker_result.get("generated_artifacts"):
            score += 0.05
        if action.output and action.request:
            score += 0.05
        return min(0.99, round(score, 3))

    def _reliability_score(self, tool_activity: list[dict[str, Any]]) -> float:
        if not tool_activity:
            return 0.75
        successes = sum(1 for item in tool_activity if item.get("success"))
        verified = sum(1 for item in tool_activity if item.get("verified"))
        ratio = successes / max(1, len(tool_activity))
        verified_ratio = verified / max(1, len(tool_activity))
        score = 0.65 + (ratio * 0.2) + (verified_ratio * 0.15)
        return min(0.99, round(score, 3))

    def _user_satisfaction_score(self, feedback_signal: dict[str, Any]) -> float:
        status = (feedback_signal.get("status") or "").lower()
        if status in {"approved", "accepted", "liked"}:
            return 0.95
        if status in {"edited", "regenerated"}:
            return 0.72
        if status in {"rejected", "cancelled"}:
            return 0.45
        return 0.8

    def _efficiency_score(self, worker_result: dict[str, Any], tool_activity: list[dict[str, Any]]) -> float:
        latency = 0
        for item in tool_activity:
            latency += int(item.get("latency_ms") or 0)
        worker_latency = float(worker_result.get("time_taken_seconds") or 0)
        if latency and worker_latency:
            combined = max(1, round((worker_latency + latency / 1000) / 2, 3))
        else:
            combined = worker_latency or 1
        score = 0.9 - min(0.25, combined / 80)
        return min(0.99, round(max(0.55, score), 3))

    def _confidence_label(self, overall_score: float) -> str:
        if overall_score >= 0.85:
            return "high"
        if overall_score >= 0.7:
            return "medium"
        return "low"

    def _notes(self, action: ActionExecution, overall_score: float, confidence_level: str) -> list[str]:
        notes: list[str] = []
        if action.output:
            notes.append("The action produced a concrete output.")
        if confidence_level == "high":
            notes.append("The outcome passed the high-confidence threshold for reuse.")
        else:
            notes.append("The outcome should be reviewed before reuse.")
        if overall_score >= 0.85:
            notes.append("The result is strong enough to influence future planning.")
        return notes

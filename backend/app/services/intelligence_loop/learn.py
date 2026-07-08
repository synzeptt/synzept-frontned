from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.intelligence_loop import LearningOutcomeIn, LearningOutcomeOut
from app.services.intelligence_loop.mock_data import MOCK_LEARNING_OUTCOMES


class LearnService:
    def __init__(self, outcomes: list[dict[str, Any]] | None = None) -> None:
        self.outcomes = deepcopy(outcomes or MOCK_LEARNING_OUTCOMES)

    def list_outcomes(self) -> list[LearningOutcomeOut]:
        return [LearningOutcomeOut(**outcome) for outcome in self.outcomes]

    def record_outcome(self, body: LearningOutcomeIn) -> LearningOutcomeOut:
        adjustment = self._adjustment_for(body.outcome)
        outcome = LearningOutcomeOut(
            id=f"learn-{len(self.outcomes) + 1:03d}",
            targetId=body.targetId,
            targetType=body.targetType,
            outcome=body.outcome,
            adjustment=adjustment,
            recordedAt="2026-07-07T09:45:00+05:30",
            note=body.note,
        )
        self.outcomes.append(outcome.model_dump())
        return outcome

    @staticmethod
    def _adjustment_for(outcome: str) -> str:
        if outcome in {"accepted", "successful"}:
            return "Increase future ranking weight for similar evidence and action shape."
        if outcome in {"rejected", "unsuccessful"}:
            return "Decrease future ranking weight and require stronger evidence next time."
        return "Keep evidence but lower urgency until the user engages again."

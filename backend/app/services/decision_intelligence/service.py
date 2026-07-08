from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.decision_intelligence import (
    DecisionDetectionOut,
    DecisionDNATraitOut,
    DecisionIntelligenceOut,
    DecisionOutcomeAnalysisOut,
    DecisionRecordOut,
    DecisionRecommendationOut,
    DecisionReviewOut,
    DecisionReviewUpdateIn,
)
from app.services.decision_intelligence.mock_data import MOCK_DECISION_INTELLIGENCE


class DecisionIntelligenceService:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = deepcopy(data or MOCK_DECISION_INTELLIGENCE)

    def snapshot(self) -> DecisionIntelligenceOut:
        return DecisionIntelligenceOut(**self.data)

    def detection_candidates(self, min_confidence: float = 0.75) -> list[DecisionDetectionOut]:
        return [
            DecisionDetectionOut(**candidate)
            for candidate in self.data["detectionCandidates"]
            if candidate["confidence"] >= min_confidence and candidate["shouldSuggestDecision"]
        ]

    def decisions(self, status: str | None = None) -> list[DecisionRecordOut]:
        rows = self.data["decisions"]
        if status:
            rows = [decision for decision in rows if decision["currentStatus"].lower() == status.lower()]
        return [DecisionRecordOut(**decision) for decision in rows]

    def decision_detail(self, decision_id: str) -> DecisionRecordOut | None:
        match = next((decision for decision in self.data["decisions"] if decision["id"] == decision_id), None)
        return DecisionRecordOut(**match) if match else None

    def reviews(self) -> list[DecisionReviewOut]:
        return [DecisionReviewOut(**review) for review in self.data["reviews"]]

    def outcome_analyses(self) -> list[DecisionOutcomeAnalysisOut]:
        return [DecisionOutcomeAnalysisOut(**analysis) for analysis in self.data["outcomeAnalyses"]]

    def decision_dna(self) -> list[DecisionDNATraitOut]:
        return [DecisionDNATraitOut(**trait) for trait in self.data["decisionDNA"]]

    def recommendations(self) -> list[DecisionRecommendationOut]:
        ranked = sorted(self.data["recommendations"], key=lambda item: (item["expectedImpact"], item["confidence"]), reverse=True)
        return [DecisionRecommendationOut(**recommendation) for recommendation in ranked]

    def update_review(self, body: DecisionReviewUpdateIn) -> dict[str, Any]:
        review = next((item for item in self.data["reviews"] if item["decisionId"] == body.decisionId), None)
        if not review:
            return {"status": "not_found", "decisionId": body.decisionId}
        review["reviewState"] = body.reviewState
        return {
            "status": "updated",
            "decisionId": body.decisionId,
            "reviewState": body.reviewState,
            "actualOutcome": body.actualOutcome,
            "lessonsLearned": body.lessonsLearned,
            "message": "Mock review update recorded. No production decision data was changed.",
        }

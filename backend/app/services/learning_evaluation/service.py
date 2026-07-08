from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.learning_evaluation import (
    EvaluationMetricsOut,
    FeedbackIn,
    LearningEvaluationDashboardOut,
    OutcomeOut,
    RecordOutcomeIn,
    RecordRecommendationIn,
    RecommendationOut,
)
from app.services.learning_evaluation.mock_data import MOCK_LEARNING_EVALUATION


class LearningEvaluationService:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = deepcopy(data or MOCK_LEARNING_EVALUATION)

    def dashboard(self) -> LearningEvaluationDashboardOut:
        self.data["metrics"] = self._metrics()
        return LearningEvaluationDashboardOut(**self.data)

    def recommendations(self) -> list[RecommendationOut]:
        return [RecommendationOut(**item) for item in self.data["recommendations"]]

    def record_recommendation(self, body: RecordRecommendationIn) -> RecommendationOut:
        recommendation = {
            "id": f"rec-{len(self.data['recommendations']) + 1}",
            "title": body.title,
            "recommendation": body.recommendation,
            "reasoningPlanId": body.reasoningPlanId,
            "decisionId": body.decisionId,
            "userId": "mock-user",
            "status": "waiting_for_outcome",
            "confidence": body.confidence,
            "createdAt": "2026-07-08T12:10:00+05:30",
            "expectedOutcomeAt": "2026-07-15T12:10:00+05:30",
            "tags": body.tags,
        }
        prediction = {
            "id": f"pred-{len(self.data['predictions']) + 1}",
            "recommendationId": recommendation["id"],
            "predictedOutcome": body.predictedOutcome,
            "probability": body.probability,
            "measurableSignal": body.measurableSignal,
            "horizonDays": body.horizonDays,
            "assumptions": ["Recorded through mock Sprint 3 API"],
        }
        confidence = {
            "id": f"conf-{recommendation['id']}-1",
            "recommendationId": recommendation["id"],
            "timestamp": recommendation["createdAt"],
            "confidence": body.confidence,
            "reason": "Initial recommendation confidence.",
        }
        self.data["recommendations"].append(recommendation)
        self.data["predictions"].append(prediction)
        self.data["confidenceHistory"].append(confidence)
        return RecommendationOut(**recommendation)

    def record_outcome(self, recommendation_id: str, body: RecordOutcomeIn) -> OutcomeOut:
        outcome = {
            "id": f"out-{recommendation_id}",
            "recommendationId": recommendation_id,
            "actualOutcome": body.actualOutcome,
            "success": body.success,
            "occurredAt": "2026-07-08T12:20:00+05:30",
            "evidence": body.evidence,
            "userFeedback": body.userFeedback,
        }
        self.data["outcomes"].append(outcome)
        recommendation = self._find_recommendation(recommendation_id)
        if recommendation:
            recommendation["status"] = "completed" if body.success else "unsuccessful"
        self._evaluate(recommendation_id, outcome)
        return OutcomeOut(**outcome)

    def feedback(self, recommendation_id: str, body: FeedbackIn) -> dict[str, str | bool]:
        recommendation = self._find_recommendation(recommendation_id)
        if not recommendation:
            return {"status": "not_found", "recorded": False, "recommendationId": recommendation_id}
        recommendation["status"] = body.feedback.lower()
        self.data["confidenceHistory"].append(
            {
                "id": f"conf-{recommendation_id}-feedback",
                "recommendationId": recommendation_id,
                "timestamp": "2026-07-08T12:25:00+05:30",
                "confidence": max(0.3, recommendation["confidence"] - (0.08 if body.feedback in {"Incorrect", "Incomplete"} else 0)),
                "reason": body.note or f"User marked recommendation as {body.feedback}.",
            }
        )
        return {"status": "feedback_recorded", "recorded": True, "recommendationId": recommendation_id}

    def _evaluate(self, recommendation_id: str, outcome: dict[str, Any]) -> None:
        prediction = next((item for item in self.data["predictions"] if item["recommendationId"] == recommendation_id), None)
        recommendation = self._find_recommendation(recommendation_id)
        if not prediction or not recommendation:
            return
        accuracy = self._accuracy(prediction["probability"], outcome["success"])
        evaluation = {
            "id": f"eval-{recommendation_id}",
            "recommendationId": recommendation_id,
            "predictionId": prediction["id"],
            "outcomeId": outcome["id"],
            "predictionAccuracy": accuracy,
            "recommendationAccepted": recommendation["status"] in {"accepted", "completed"},
            "recommendationSuccessful": outcome["success"],
            "timeToOutcomeHours": 1,
            "feedbackScore": self._feedback_score(outcome.get("userFeedback")),
            "summary": "Mock evaluation compared predicted probability with recorded outcome.",
            "createdAt": "2026-07-08T12:21:00+05:30",
        }
        lesson = {
            "id": f"lesson-{recommendation_id}",
            "evaluationId": evaluation["id"],
            "title": "Outcome updated recommendation calibration",
            "lesson": "Successful outcomes raise confidence in similar future recommendations; failed outcomes reduce it.",
            "appliesTo": recommendation["tags"],
            "confidenceDelta": 0.04 if outcome["success"] else -0.06,
            "decisionProfileUpdate": "Update mock Decision Profile calibration from evaluated outcome.",
        }
        self.data["evaluations"].append(evaluation)
        self.data["lessons"].append(lesson)

    def _metrics(self) -> dict[str, float]:
        evaluations = self.data["evaluations"]
        recommendations = self.data["recommendations"]
        if not evaluations:
            return EvaluationMetricsOut(
                predictionAccuracy=0,
                recommendationAcceptanceRate=0,
                recommendationSuccessRate=0,
                averageTimeToOutcomeHours=0,
                userFeedbackScore=0,
            ).dict()
        return {
            "predictionAccuracy": round(sum(item["predictionAccuracy"] for item in evaluations) / len(evaluations), 2),
            "recommendationAcceptanceRate": round(len([item for item in recommendations if item["status"] in {"accepted", "completed"}]) / len(recommendations), 2),
            "recommendationSuccessRate": round(len([item for item in evaluations if item["recommendationSuccessful"]]) / len(evaluations), 2),
            "averageTimeToOutcomeHours": round(sum(item["timeToOutcomeHours"] for item in evaluations) / len(evaluations), 1),
            "userFeedbackScore": round(sum(item["feedbackScore"] for item in evaluations) / len(evaluations), 2),
        }

    def _find_recommendation(self, recommendation_id: str) -> dict[str, Any] | None:
        return next((item for item in self.data["recommendations"] if item["id"] == recommendation_id), None)

    def _accuracy(self, probability: float, success: bool) -> float:
        expected = probability if success else 1 - probability
        return round(max(0, min(1, expected)), 2)

    def _feedback_score(self, feedback: str | None) -> float:
        scores = {"Helpful": 1.0, "Incorrect": 0.0, "Outdated": 0.35, "Incomplete": 0.45}
        return scores.get(feedback or "", 0.6)

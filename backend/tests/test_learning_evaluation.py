from app.schemas.learning_evaluation import FeedbackIn, RecordOutcomeIn, RecordRecommendationIn
from app.services.learning_evaluation import LearningEvaluationService


def test_dashboard_includes_recommendation_learning_entities_and_metrics():
    dashboard = LearningEvaluationService().dashboard()

    assert dashboard.recommendations
    assert dashboard.predictions
    assert dashboard.outcomes
    assert dashboard.evaluations
    assert dashboard.lessons
    assert dashboard.confidenceHistory
    assert dashboard.metrics.predictionAccuracy > 0


def test_record_recommendation_creates_waiting_item_with_prediction_and_confidence_history():
    service = LearningEvaluationService()

    recommendation = service.record_recommendation(
        RecordRecommendationIn(
            title="Use evidence-backed response plan",
            recommendation="Use the planner output as the source of truth.",
            reasoningPlanId="reasoning-test-plan",
            decisionId="decision-review-before-graph-save",
            confidence=0.81,
            predictedOutcome="Response consistency improves.",
            probability=0.77,
            measurableSignal="planner_preserved",
            tags=["reasoning_engine"],
        )
    )
    dashboard = service.dashboard()

    assert recommendation.status == "waiting_for_outcome"
    assert any(prediction.recommendationId == recommendation.id for prediction in dashboard.predictions)
    assert any(item.recommendationId == recommendation.id for item in dashboard.confidenceHistory)


def test_record_outcome_creates_evaluation_and_lesson():
    service = LearningEvaluationService()
    recommendation = service.record_recommendation(
        RecordRecommendationIn(
            title="Evaluate outcome",
            recommendation="Record reality after prediction horizon.",
            reasoningPlanId="reasoning-plan",
            confidence=0.7,
            predictedOutcome="Outcome will be successful.",
            probability=0.72,
            measurableSignal="success",
        )
    )

    outcome = service.record_outcome(
        recommendation.id,
        RecordOutcomeIn(actualOutcome="Outcome was successful.", success=True, evidence=["mock evidence"], userFeedback="Helpful"),
    )
    dashboard = service.dashboard()

    assert outcome.success is True
    assert any(evaluation.recommendationId == recommendation.id for evaluation in dashboard.evaluations)
    assert any(lesson.evaluationId == f"eval-{recommendation.id}" for lesson in dashboard.lessons)


def test_feedback_updates_recommendation_status_and_confidence_history():
    service = LearningEvaluationService()

    result = service.feedback("rec-ask-clarifying-question", FeedbackIn(feedback="Incomplete", note="Too cautious for this sprint."))
    dashboard = service.dashboard()

    assert result["recorded"] is True
    assert next(item for item in dashboard.recommendations if item.id == "rec-ask-clarifying-question").status == "incomplete"
    assert any(item.reason == "Too cautious for this sprint." for item in dashboard.confidenceHistory)


def test_metrics_track_acceptance_success_time_and_feedback():
    metrics = LearningEvaluationService().dashboard().metrics

    assert 0 <= metrics.predictionAccuracy <= 1
    assert 0 <= metrics.recommendationAcceptanceRate <= 1
    assert 0 <= metrics.recommendationSuccessRate <= 1
    assert metrics.averageTimeToOutcomeHours > 0
    assert 0 <= metrics.userFeedbackScore <= 1

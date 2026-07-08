from app.schemas.trust_engine import TrustFeedbackIn
from app.services.trust_engine_service import TrustEngineService


def test_trust_engine_returns_recommendations_and_feedback_acknowledgement():
    service = TrustEngineService()
    recommendations = service.list_recommendations()
    feedback = service.feedback(
        TrustFeedbackIn(recommendationId="trust-1", feedbackType="Helpful", note="Great explanation")
    )

    assert recommendations
    assert recommendations[0].confidenceLevel in {"High", "Medium", "Low"}
    assert feedback.status == "recorded"

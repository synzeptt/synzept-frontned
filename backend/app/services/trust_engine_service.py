from __future__ import annotations

from app.schemas.trust_engine import TrustFeedbackIn, TrustFeedbackOut, TrustRecommendationOut
from app.services.trust_engine_mock_data import MOCK_RECOMMENDATIONS


class TrustEngineService:
    def __init__(self) -> None:
        self.recommendations = MOCK_RECOMMENDATIONS

    def list_recommendations(self) -> list[TrustRecommendationOut]:
        return [TrustRecommendationOut(**item) for item in self.recommendations]

    def feedback(self, payload: TrustFeedbackIn) -> TrustFeedbackOut:
        return TrustFeedbackOut(
            recommendationId=payload.recommendationId,
            feedbackType=payload.feedbackType,
            status="recorded",
            message="Feedback captured for future recommendation tuning.",
        )

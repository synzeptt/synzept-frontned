from __future__ import annotations

from app.schemas.intelligence_loop import (
    ActionApprovalIn,
    IntelligenceEventOut,
    IntelligenceLoopSnapshotOut,
    LearningOutcomeIn,
    LearningOutcomeOut,
)
from app.services.intelligence_loop.act import ActService
from app.services.intelligence_loop.learn import LearnService
from app.services.intelligence_loop.observe import ObserveService
from app.services.intelligence_loop.predict import PredictService
from app.services.intelligence_loop.recommend import RecommendService
from app.services.intelligence_loop.understand import UnderstandService


class IntelligenceLoopService:
    def __init__(
        self,
        observe: ObserveService | None = None,
        understand: UnderstandService | None = None,
        predict: PredictService | None = None,
        recommend: RecommendService | None = None,
        act: ActService | None = None,
        learn: LearnService | None = None,
    ) -> None:
        self.observe = observe or ObserveService()
        self.understand = understand or UnderstandService()
        self.predict = predict or PredictService()
        self.recommend = recommend or RecommendService()
        self.act = act or ActService()
        self.learn = learn or LearnService()

    def snapshot(self) -> IntelligenceLoopSnapshotOut:
        events = self.observe.collect_events()
        user_model = self.understand.update_user_model(events)
        predictions = self.predict.generate_predictions(events, user_model)
        recommendations = self.recommend.rank_recommendations(predictions, user_model)
        action_requests = self.act.create_action_requests(recommendations)
        learning_outcomes = self.learn.list_outcomes()
        return IntelligenceLoopSnapshotOut(
            generatedAt="2026-07-07T09:45:00+05:30",
            events=events,
            userModel=user_model,
            predictions=predictions,
            recommendations=recommendations,
            actionRequests=action_requests,
            learningOutcomes=learning_outcomes,
            loopHealth={
                "status": "mock_ready",
                "observedEvents": len(events),
                "predictions": len(predictions),
                "recommendations": len(recommendations),
                "pendingApprovals": len(action_requests),
                "learningOutcomes": len(learning_outcomes),
            },
        )

    def observe_event(self, event: IntelligenceEventOut) -> dict[str, str]:
        return {"status": "observed", "eventId": event.id, "message": "Event accepted into mock Intelligence Loop."}

    def record_approval(self, body: ActionApprovalIn) -> dict[str, str | bool | None]:
        return self.act.record_approval(body)

    def record_outcome(self, body: LearningOutcomeIn) -> LearningOutcomeOut:
        return self.learn.record_outcome(body)

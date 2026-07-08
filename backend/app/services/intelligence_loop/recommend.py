from __future__ import annotations

from app.schemas.intelligence_loop import PredictionOut, RecommendationOut, UserModelOut


class RecommendService:
    def rank_recommendations(self, predictions: list[PredictionOut], user_model: UserModelOut) -> list[RecommendationOut]:
        recommendations = [
            RecommendationOut(
                id="rec-focus-beta-invite",
                title="Send the private beta invite before adding new surface work",
                action="Draft a short beta invite with one onboarding feedback ask.",
                why="The deadline risk is high and the commitment involves people waiting on you.",
                expectedImpact=88,
                effort="15 min",
                confidence=0.84,
                rankedScore=0,
                linkedPredictionIds=["pred-beta-deadline-risk"],
            ),
            RecommendationOut(
                id="rec-wire-intelligence-loop",
                title="Make every V2 surface emit Intelligence Loop events",
                action="Use the common event model for memory, action, opportunity, mission, and trust updates.",
                why="This reduces fragmentation and gives the product one shared learning substrate.",
                expectedImpact=94,
                effort="45 min",
                confidence=0.82,
                rankedScore=0,
                linkedPredictionIds=["pred-fragmentation-blocker", "pred-v2-launch-probability"],
            ),
            RecommendationOut(
                id="rec-promote-memory-feed",
                title="Use Memory Feed as the first consumer of predictions",
                action="Surface top predictions, recommendations, and approval requests inside the first screen.",
                why="The feed already answers what changed, what matters, and what needs attention.",
                expectedImpact=86,
                effort="30 min",
                confidence=0.78,
                rankedScore=0,
                linkedPredictionIds=["pred-retention-opportunity"],
            ),
        ]
        priority_confidence = max((signal.confidence for signal in user_model.priorities), default=0.5)
        for recommendation in recommendations:
            recommendation.rankedScore = round(
                recommendation.expectedImpact * 0.55 + recommendation.confidence * 100 * 0.25 + priority_confidence * 100 * 0.20,
                1,
            )
        return sorted(recommendations, key=lambda item: item.rankedScore, reverse=True)

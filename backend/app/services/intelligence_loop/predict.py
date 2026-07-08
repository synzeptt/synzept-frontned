from __future__ import annotations

from app.schemas.intelligence_loop import EvidenceOut, IntelligenceEventOut, PredictionOut, UserModelOut


class PredictService:
    def generate_predictions(self, events: list[IntelligenceEventOut], user_model: UserModelOut) -> list[PredictionOut]:
        return [
            PredictionOut(
                id="pred-v2-launch-probability",
                kind="goal_completion_probability",
                title="V2 foundation likely to reach usable prototype this week",
                forecast="The core surfaces exist; integration through Memory Feed and Intelligence Loop is the remaining leverage point.",
                probability=0.74,
                confidence=self._avg_confidence([signal.confidence for signal in user_model.goals + user_model.priorities]),
                horizon="7 days",
                supportingEvidence=self._evidence(events, ["Synzept V2", "integration_needed", "Memory Feed"]),
                riskLevel="medium",
            ),
            PredictionOut(
                id="pred-beta-deadline-risk",
                kind="missed_deadline_risk",
                title="Beta invite follow-up has elevated miss risk",
                forecast="The commitment is external, time-sensitive, and competing with platform implementation work.",
                probability=0.68,
                confidence=0.81,
                horizon="24 hours",
                supportingEvidence=self._evidence(events, ["external_commitment", "deadline", "Aarav"]),
                riskLevel="high",
            ),
            PredictionOut(
                id="pred-fragmentation-blocker",
                kind="emerging_blocker",
                title="Feature fragmentation may slow V2 clarity",
                forecast="Several intelligence surfaces are useful individually but need one shared loop contract.",
                probability=0.72,
                confidence=0.78,
                horizon="3 days",
                supportingEvidence=self._evidence(events, ["integration_needed", "home_screen", "safety_boundary"]),
                riskLevel="medium",
            ),
            PredictionOut(
                id="pred-retention-opportunity",
                kind="opportunity_forecast",
                title="Daily recall can become the retention ritual",
                forecast="A ranked first screen that remembers commitments and progress creates immediate return value.",
                probability=0.79,
                confidence=0.76,
                horizon="14 days",
                supportingEvidence=self._evidence(events, ["proactive_recall", "north_star", "retention"]),
                riskLevel="low",
            ),
        ]

    @staticmethod
    def _avg_confidence(values: list[float]) -> float:
        if not values:
            return 0.5
        return round(sum(values) / len(values), 2)

    @staticmethod
    def _evidence(events: list[IntelligenceEventOut], needles: list[str]) -> list[EvidenceOut]:
        matches = []
        for event in events:
            haystack = " ".join([event.title, event.description, *event.entities, *event.signals]).lower()
            if any(needle.lower() in haystack for needle in needles):
                matches.append(EvidenceOut(sourceId=event.id, sourceType=event.source, summary=event.title, strength=max(event.importance, event.urgency)))
        return matches[:4]

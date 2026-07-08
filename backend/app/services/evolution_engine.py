from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.services.evolution_engine_mock_data import MOCK_EVOLUTION_DATA


@dataclass
class EvolutionInsight:
    title: str
    summary: str
    evidence: list[str]
    confidence: str
    impact: str
    source: str


@dataclass
class EvolutionRecommendation:
    title: str
    summary: str
    rationale: str
    estimatedImpact: str
    priority: str
    signal: str


class EvolutionEngineService:
    """Mocked internal intelligence engine for founder and product analysis."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or MOCK_EVOLUTION_DATA

    def get_product_insights(self) -> list[dict[str, Any]]:
        return [
            {
                "title": insight["title"],
                "summary": insight["summary"],
                "evidence": insight["evidence"],
                "confidence": insight["confidence"],
                "impact": insight["impact"],
                "source": insight["source"],
            }
            for insight in self.data.get("insights", [])
        ]

    def get_recommendations(self) -> list[dict[str, Any]]:
        return [
            {
                "title": recommendation["title"],
                "summary": recommendation["summary"],
                "rationale": recommendation["rationale"],
                "estimatedImpact": recommendation["estimatedImpact"],
                "priority": recommendation["priority"],
                "signal": recommendation["signal"],
            }
            for recommendation in self.data.get("recommendations", [])
        ]

    def get_feature_adoption(self) -> dict[str, Any]:
        features = self.data.get("feature_usage", [])
        return {
            "topFeatures": [
                {
                    "feature": feature["feature"],
                    "adoption": feature["adoption"],
                    "engagement": feature["engagement"],
                    "signal": feature["signal"],
                }
                for feature in sorted(features, key=lambda item: item["adoption"], reverse=True)
            ],
            "lowestAdoption": [
                {
                    "feature": feature["feature"],
                    "adoption": feature["adoption"],
                    "engagement": feature["engagement"],
                    "signal": feature["signal"],
                }
                for feature in sorted(features, key=lambda item: item["adoption"])[:3]
            ],
        }

    def get_onboarding_analysis(self) -> dict[str, Any]:
        onboarding = self.data.get("onboarding", {})
        steps = onboarding.get("steps", [])
        drop_offs = [
            {
                "step": step["step"],
                "completion": step["completion"],
                "dropOff": step["drop_off"],
            }
            for step in steps
        ]
        return {
            "completionRate": onboarding.get("completion_rate", 0),
            "dropOffs": drop_offs,
            "highestDropOff": max(drop_offs, key=lambda item: item["dropOff"], default={"step": "unknown", "dropOff": 0}),
        }

    def get_retention_summary(self) -> dict[str, Any]:
        retention = self.data.get("retention", {})
        return {
            "retentionRate": retention.get("retention_rate", 0),
            "returningUsers": retention.get("returning_users", 0),
            "weeklyActiveUsers": retention.get("weekly_active_users", 0),
            "trend": retention.get("trend", "stable"),
            "cohortNotes": retention.get("cohort_notes", []),
        }

    def get_founder_dashboard(self) -> dict[str, Any]:
        return {
            "productHealth": {
                "score": 78,
                "label": "Healthy with onboarding friction",
                "trend": "up",
            },
            "activationFunnel": {
                "signups": 842,
                "completedOnboarding": 530,
                "returnedUsers": 345,
            },
            "retentionTrends": [
                {"week": "W1", "retention": 0.41},
                {"week": "W2", "retention": 0.47},
                {"week": "W3", "retention": 0.52},
            ],
            "topRecommendations": self.get_recommendations()[:2],
            "recentIssues": [
                "Workspace setup feels too long",
                "Search is not visible in the early workflow",
            ],
        }

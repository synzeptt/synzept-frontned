from __future__ import annotations

from typing import Any

from app.schemas.opportunity import OpportunityOut, OpportunityScoreBreakdownOut
from app.services.opportunity_mock_data import MOCK_OPPORTUNITY_HISTORY, MOCK_OPPORTUNITIES


class OpportunityEngineService:
    def __init__(self, opportunities: list[dict[str, Any]] | None = None, history: list[dict[str, Any]] | None = None) -> None:
        self.opportunities = opportunities or MOCK_OPPORTUNITIES
        self.history = history or MOCK_OPPORTUNITY_HISTORY

    def current_opportunities(self, limit: int = 5) -> list[OpportunityOut]:
        ranked = sorted(self.opportunities, key=lambda item: item["score"], reverse=True)
        return [OpportunityOut(**item) for item in ranked[:limit]]

    def history_items(self) -> list[dict[str, Any]]:
        return list(self.history)

    def feedback(self, opportunity_id: str, action: str, note: str | None = None) -> dict[str, Any]:
        self.history.append({"opportunityId": opportunity_id, "status": action, "note": note})
        return {"status": "recorded", "opportunityId": opportunity_id, "action": action}

    def score_breakdown(self, opportunity_id: str) -> OpportunityScoreBreakdownOut | None:
        match = next((item for item in self.opportunities if item["id"] == opportunity_id), None)
        if not match:
            return None
        score = match["score"]
        impact_score = 90 if match["impact"] == "High" else 75
        confidence_score = 90 if match["confidence"] == "High" else 75
        urgency_score = 90 if match["urgency"] == "High" else 75
        return OpportunityScoreBreakdownOut(
            opportunityId=opportunity_id,
            impactScore=impact_score,
            confidenceScore=confidence_score,
            urgencyScore=urgency_score,
            totalScore=score,
        )

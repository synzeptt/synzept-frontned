from __future__ import annotations

from copy import deepcopy

from app.schemas.memory_feed import MemoryFeedOut
from app.services.memory_feed.mock_data import MOCK_MEMORY_FEED

FACTOR_WEIGHTS = {
    "Relevance": 0.30,
    "Urgency": 0.25,
    "Importance": 0.25,
    "Recency": 0.15,
    "Feedback": 0.05,
}


class MemoryFeedService:
    def __init__(self, data: dict | None = None) -> None:
        self.data = deepcopy(data or MOCK_MEMORY_FEED)

    def get_feed(self, limit: int = 7) -> MemoryFeedOut:
        cards = self.rank_cards(self.data["cards"], limit=limit)
        return MemoryFeedOut(
            generatedAt=self.data["generatedAt"],
            nextRefreshAt=self.data["nextRefreshAt"],
            refreshLabel=self.data["refreshLabel"],
            cards=cards,
        )

    def refresh_feed(self, limit: int = 7) -> MemoryFeedOut:
        return self.get_feed(limit=limit)

    @staticmethod
    def score_card(card: dict) -> float:
        score = sum(factor["value"] * FACTOR_WEIGHTS.get(factor["label"], 0) for factor in card.get("factors", []))
        if card.get("pinned"):
            score += 12
        if card.get("status") in {"archived", "snoozed"}:
            score -= 100
        return round(score, 1)

    @classmethod
    def rank_cards(cls, cards: list[dict], limit: int = 7) -> list[dict]:
        ranked_cards = []
        for card in cards:
            if card.get("status") in {"archived", "snoozed"}:
                continue
            ranked_card = {**card, "score": cls.score_card(card), "status": card.get("status", "active")}
            ranked_cards.append(ranked_card)

        ranked_cards.sort(key=lambda card: (not card.get("pinned", False), -card["score"]))
        return ranked_cards[:limit]

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.privacy_intelligence import (
    GlobalPatternOut,
    PrivacyContributionSettingsIn,
    PrivacyContributionSettingsOut,
    PrivacyIntelligenceOut,
    PrivacyRecommendationOut,
)
from app.services.privacy_intelligence.mock_data import MOCK_PRIVACY_INTELLIGENCE


class PrivacyIntelligenceService:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = deepcopy(data or MOCK_PRIVACY_INTELLIGENCE)

    def snapshot(self) -> PrivacyIntelligenceOut:
        return PrivacyIntelligenceOut(**self.data)

    def recommendations(self) -> list[PrivacyRecommendationOut]:
        ranked = sorted(self.data["recommendations"], key=lambda item: (item["expectedImpact"], item["confidence"]), reverse=True)
        return [PrivacyRecommendationOut(**item) for item in ranked]

    def global_patterns(self) -> list[GlobalPatternOut]:
        return [GlobalPatternOut(**item) for item in self.data["globalPatterns"]]

    def contribution_settings(self) -> PrivacyContributionSettingsOut:
        return PrivacyContributionSettingsOut(**self.data["contributionSettings"])

    def update_contribution_settings(self, body: PrivacyContributionSettingsIn) -> PrivacyContributionSettingsOut:
        self.data["contributionSettings"]["optedIn"] = body.optedIn
        self.data["contributionSettings"]["mode"] = body.mode
        self.data["contributionSettings"]["lastUpdatedAt"] = "2026-07-07T18:55:00+05:30"
        return self.contribution_settings()

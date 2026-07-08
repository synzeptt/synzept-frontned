from __future__ import annotations

from app.services.coach.mock_data import MOCK_COACH_BRIEF


class CoachService:
    def __init__(self) -> None:
        self.brief = MOCK_COACH_BRIEF

    def get_morning_brief(self) -> dict:
        return self.brief["morning"]

    def get_midday_checkin(self) -> dict:
        return self.brief["midday"]

    def get_evening_reflection(self) -> dict:
        return self.brief["evening"]

    def get_weekly_summary(self) -> dict:
        return self.brief["weekly"]

    def get_coaching_state(self) -> dict:
        return {
            "coachingEnabled": True,
            "snoozed": False,
            "messageLimit": "Low",
            "tone": "Supportive and calm",
            "nextRecommendation": self.get_morning_brief()["recommendedAction"],
        }

from app.services.coach.service import CoachService


def test_coach_returns_brief_and_state():
    service = CoachService()

    assert service.get_morning_brief()["title"] == "Morning Brief"
    assert service.get_midday_checkin()["title"] == "Midday Check-in"
    assert service.get_evening_reflection()["title"] == "Evening Reflection"
    assert service.get_weekly_summary()["title"] == "Weekly Coaching Summary"
    assert service.get_coaching_state()["coachingEnabled"] is True

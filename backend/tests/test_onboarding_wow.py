from app.services.onboarding_wow_service import OnboardingWowService
from app.schemas.onboarding_wow import OnboardingWowAdvanceIn


def test_onboarding_wow_service_builds_initial_results():
    service = OnboardingWowService()
    started = service.start()
    advanced = service.advance(OnboardingWowAdvanceIn(focus_area="launch readiness", goal="ship the beta"))

    assert started.progress == 10
    assert advanced.progress == 75
    assert advanced.insights
    assert advanced.nextAction

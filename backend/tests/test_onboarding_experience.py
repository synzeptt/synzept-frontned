from types import SimpleNamespace
from uuid import uuid4

from app.models.user import User
from app.schemas.onboarding import FirstRunIntelligenceIn, OnboardingContextIn
from app.services.onboarding_service import OnboardingService


def test_onboarding_context_trims_lightweight_lists():
    body = OnboardingContextIn(
        display_name="Alex",
        goals=[" Ship launch ", "", "   ", "Write memo"],
        current_priorities=[" First priority ", "Second priority"],
    )

    assert body.goals == ["Ship launch", "Write memo"]
    assert body.current_priorities == ["First priority", "Second priority"]


def test_first_run_payload_keeps_confirmed_understanding():
    body = FirstRunIntelligenceIn(
        building="Synzept home",
        top_goals=[" Make users feel understood "],
        current_focus="Onboarding",
        important_projects=[" First 60 seconds "],
        success_90_days="Activated users return daily.",
        struggling_with="Too much setup",
        help_continue="Continue onboarding",
        generated_current_mission="Make Synzept feel like it already knows the user.",
        generated_open_loops=[" Clarify first moment ", "", "Generate Daily Brief"],
        generated_suggested_actions=[" Review onboarding flow ", "Ship Home V3 handoff"],
    )

    assert body.generated_current_mission == "Make Synzept feel like it already knows the user."
    assert body.generated_open_loops == ["Clarify first moment", "Generate Daily Brief"]
    assert body.generated_suggested_actions == ["Review onboarding flow", "Ship Home V3 handoff"]


def test_onboarding_progress_tracks_resume_and_initialized_systems():
    user = User(id=uuid4(), email="alex@example.com", preferences={})
    service = OnboardingService(SimpleNamespace())

    service._mark_step(user, "welcome", initialized="welcome_flow", resume_step="profile")
    service._mark_step(user, "profile", initialized="profile", resume_step="workspace")
    service._skip_step(user, "workspace")

    onboarding = user.preferences["onboarding"]
    assert onboarding["completed_steps"] == ["welcome", "profile"]
    assert onboarding["initialized_systems"] == ["welcome_flow", "profile"]
    assert onboarding["resume_step"] == "workspace"
    assert onboarding["skipped_steps"] == ["workspace"]


def test_dashboard_preview_uses_priorities_before_empty_state():
    profile = SimpleNamespace(goals=["Launch Synzept"], routines={"priorities": ["Finish onboarding"]})

    preview = OnboardingService._dashboard_preview(profile, has_workspace=True, has_memories=True)

    assert preview.suggested_priorities[0] == "Finish onboarding"
    assert "Starter project" in preview.starter_structure
    assert "Memory context" in preview.starter_structure
    assert len(preview.next_actions) == 2

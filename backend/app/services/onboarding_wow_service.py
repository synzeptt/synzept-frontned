from __future__ import annotations

from app.schemas.onboarding_wow import OnboardingWowAdvanceIn, OnboardingWowAdvanceOut, OnboardingWowStartOut


class OnboardingWowService:
    def start(self) -> OnboardingWowStartOut:
        return OnboardingWowStartOut(
            step="interview",
            title="Welcome to the 10-Minute Wow",
            description="We'll learn enough about you to create your first mission, Daily OS, and action center in minutes.",
            progress=10,
            nextLabel="Start the interview",
        )

    def advance(self, payload: OnboardingWowAdvanceIn) -> OnboardingWowAdvanceOut:
        summary = f"You want to move faster on {payload.focus_area or 'your priorities'} and keep momentum around {payload.goal or 'your main objective'}."
        return OnboardingWowAdvanceOut(
            step="results",
            progress=75,
            mission="Build a calm operating system for your next big move",
            missionWhy="Synzept identified a strong need for clarity, momentum, and fewer open loops.",
            dailyOs="Protect one deep work block and one review ritual each day.",
            actionCenter=["Review your next milestone", "Decline low-value scope", "Capture one insight before the day ends"],
            lifeGraphPreview=["Mission: Launch readiness", "Decision: Focus before scope expansion", "Pattern: Weekly review improves confidence"],
            insights=[
                "You move faster when you define milestones early.",
                "Your best decisions follow evidence and reflection.",
                "Scope control protects momentum more than extra features.",
            ],
            nextAction="Schedule a 20-minute review and lock your first milestone.",
            summary=summary,
            requiresApproval=False,
        )

    def approve(self) -> dict:
        return {
            "step": "success",
            "progress": 100,
            "message": "Your first wow experience is ready. Synzept now understands your direction and your next best move.",
        }

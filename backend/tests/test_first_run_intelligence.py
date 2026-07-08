from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.autonomous_workspace import ExecutionPlan
from app.models.daily_brief_phase8 import DailyBriefSnapshot
from app.models.feedback import UsageEvent
from app.models.project import Project
from app.models.project_intelligence_phase2 import OpenLoop
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.onboarding import FirstRunIntelligenceIn
from app.services.onboarding_service import OnboardingService
from app.services.open_loops_engine_service import OpenLoopsEngineService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'first-run.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_first_run_intelligence_seeds_personal_workspace(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="first-run@example.com")
        session.add(user)
        await session.flush()

        result = await OnboardingService(session).complete_first_run_intelligence(
            user,
            FirstRunIntelligenceIn(
                building="Synzept",
                top_goals=["Get 100 paying users", "Launch V1"],
                current_focus="Continue the first 60-second experience",
                important_projects=["Synzept Launch", "Founder Dashboard"],
                success_90_days="100 paying users with a reliable onboarding path.",
                struggling_with="Activation feels too generic",
                help_continue="Continue onboarding after signup",
                generated_current_mission="Make Synzept feel understood in the first minute",
                generated_open_loops=["Tighten signup handoff", "Confirm first Daily Brief"],
                generated_suggested_actions=["Review the onboarding flow", "Open Home V3 after confirmation"],
            ),
        )

        projects = list((await session.execute(select(Project).where(Project.user_id == user_id))).scalars())
        understanding = list((await session.execute(select(UserUnderstanding).where(UserUnderstanding.user_id == user_id))).scalars())
        loops = list((await session.execute(select(OpenLoop))).scalars())
        plans = list((await session.execute(select(ExecutionPlan).where(ExecutionPlan.user_id == user_id))).scalars())
        briefs = list((await session.execute(select(DailyBriefSnapshot).where(DailyBriefSnapshot.user_id == user_id))).scalars())
        events = list((await session.execute(select(UsageEvent).where(UsageEvent.user_id == user_id))).scalars())

        assert result.state == "complete"
        assert result.welcome_brief["currentMission"] == "Make Synzept feel understood in the first minute"
        assert result.welcome_brief["openLoops"] == ["Tighten signup handoff", "Confirm first Daily Brief"]
        assert result.welcome_brief["suggestedFirstActions"][0] == "Review the onboarding flow"
        assert result.welcome_brief["dailyBrief"]["recommendedNextAction"] == "Review the onboarding flow"
        assert result.dashboard_preview.next_actions
        assert result.analytics.day_1_activation is True
        assert result.analytics.daily_brief_opens == 0
        assert user.onboarding_state == "complete"
        assert {project.name for project in projects} >= {"Synzept Launch", "Founder Dashboard"}
        assert any(item.category == "current_mission" and item.value == "Make Synzept feel understood in the first minute" for item in understanding)
        assert any(item.category == "current_focus" and "first 60-second" in item.value for item in understanding)
        assert loops
        assert plans
        assert briefs
        assert "first_run_activation_completed" in {event.event_type for event in events}

        await OpenLoopsEngineService(session).complete(user_id, "open_loop", loops[0].id)
        analytics = await OnboardingService(session).analytics.summary(user_id, user.preferences)
        assert analytics.open_loop_completions == 1

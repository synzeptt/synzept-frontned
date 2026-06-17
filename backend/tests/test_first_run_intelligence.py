from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.autonomous_workspace import ExecutionPlan
from app.models.project import Project
from app.models.project_intelligence_phase2 import OpenLoop
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.onboarding import FirstRunIntelligenceIn
from app.services.onboarding_service import OnboardingService


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
                current_focus="Payments and onboarding",
                important_projects=["Synzept Launch", "Founder Dashboard"],
                success_90_days="100 paying users with a reliable onboarding path.",
            ),
        )

        projects = list((await session.execute(select(Project).where(Project.user_id == user_id))).scalars())
        understanding = list((await session.execute(select(UserUnderstanding).where(UserUnderstanding.user_id == user_id))).scalars())
        loops = list((await session.execute(select(OpenLoop))).scalars())
        plans = list((await session.execute(select(ExecutionPlan).where(ExecutionPlan.user_id == user_id))).scalars())

        assert result.state == "complete"
        assert result.welcome_brief["currentMission"] == "Build Synzept"
        assert result.dashboard_preview.next_actions
        assert user.onboarding_state == "complete"
        assert {project.name for project in projects} >= {"Synzept Launch", "Founder Dashboard"}
        assert any(item.category == "current_mission" and item.value == "Build Synzept" for item in understanding)
        assert any(item.category == "current_focus" and "Payments" in item.value for item in understanding)
        assert loops
        assert plans

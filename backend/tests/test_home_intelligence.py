from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.api.home import get_home, refresh_home
from app.database.base import Base
from app.models.conversation import Conversation
from app.models.daily_summary import DailySummary
from app.models.memory import Memory
from app.models.project import Project
from app.models.project_intelligence import ProjectDecision, ProjectOpenLoop
from app.models.task import Task
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.services.home_intelligence_service import HomeIntelligenceService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'home-intelligence.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_home_intelligence_generates_operating_system_from_all_sources(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="home-layer@example.com", display_name="Ari")
        project = Project(
            user_id=user_id,
            name="Synzept Launch",
            description="Ship a calm continuity OS",
            current_focus="Finish the Home Intelligence Layer",
            recommended_next_step="Review the generated home response",
        )
        session.add_all([user, project])
        await session.flush()
        session.add_all(
            [
                UserUnderstanding(user_id=user_id, category="missions", title="Mission", value="Build a personal operating system", source="user"),
                UserUnderstanding(user_id=user_id, category="open_loops", title="Open Loops", value="Confirm launch checklist", source="user"),
                Memory(user_id=user_id, memory_type="goals", content="My goal is to launch Synzept this month.", summary="Launch Synzept this month", confidence=0.9),
                Conversation(user_id=user_id, title="Pricing discussion", summary="Review launch pricing", active_intent="Decide launch pricing", project_id=project.id),
                Task(user_id=user_id, title="Write launch notes", description="Needed before launch", priority="high", status="todo", project_id=project.id),
                ProjectOpenLoop(project_id=project.id, loop="Choose onboarding copy", status="open"),
                ProjectDecision(project_id=project.id, decision="Pricing tier", status="open"),
                DailySummary(user_id=user_id, summary_date=__import__("datetime").date.today(), summary_kind="morning", summary="Launch focus", unfinished_priorities=["Follow up on beta feedback"], insights=[]),
            ]
        )
        await session.flush()

        home = await HomeIntelligenceService(session).get_home(user)

        assert home.mission == "Build a personal operating system"
        assert home.focus == "Finish the Home Intelligence Layer"
        assert home.open_loops
        assert home.suggested_action.title
        assert home.continue_context.prompt.startswith("Continue working from Synzept Home.")
        assert home.source_counts["user_understanding"] > 0
        assert home.source_counts["previous_conversations"] > 0
        assert home.source_counts["decisions"] > 0


@pytest.mark.asyncio
async def test_home_intelligence_has_graceful_empty_state(session_factory):
    async with session_factory() as session:
        user = User(id=uuid4(), email="empty-home@example.com")
        session.add(user)
        await session.flush()

        home = await HomeIntelligenceService(session).get_home(user)

        assert home.empty_state is True
        assert home.mission.startswith("Add a mission")
        assert home.focus.startswith("Choose the one thing")
        assert home.open_loops == []
        assert home.suggested_action.title == "Capture one priority for today."


@pytest.mark.asyncio
async def test_home_api_functions_return_and_refresh_home(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="home-api@example.com")
        session.add_all(
            [
                user,
                Memory(user_id=user_id, memory_type="goals", content="My mission is to finish Home Intelligence.", summary="Finish Home Intelligence", confidence=0.9),
            ]
        )
        await session.flush()

        refreshed = await refresh_home(user=user, session=session)
        fetched = await get_home(user=user, session=session)

        assert refreshed.mission
        assert fetched.continue_context.prompt

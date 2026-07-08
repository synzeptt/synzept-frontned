from datetime import date
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.conversation import Conversation
from app.models.goal import Goal
from app.models.memory import Memory
from app.models.project import Project
from app.models.project_intelligence import ProjectOpenLoop
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.models.workspace_activity import WorkspaceActivity
from app.services.continuity_mode_service import ContinuityModeService
from app.services.continue_context_service import ContinueContextService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'continuity-mode.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_continuity_mode_restores_where_user_left_off(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="return@example.com", display_name="Piyush")
        project = Project(
            user_id=user_id,
            name="Synzept deployment",
            description="Ship the product calmly.",
            current_focus="Stabilize Azure deployment",
            recommended_next_step="Run a first-time user experience audit",
        )
        session.add_all([user, project])
        await session.flush()
        session.add_all(
            [
                Goal(user_id=user_id, project_id=project.id, title="Get first users"),
                Conversation(
                    user_id=user_id,
                    project_id=project.id,
                    title="Deployment recovery",
                    active_intent="Continue Synzept deployment",
                ),
                ProjectOpenLoop(project_id=project.id, loop="Simplify product UX", status="open"),
                TimelineEvent(
                    user_id=user_id,
                    project_id=project.id,
                    event_type="progress",
                    title="Backend deployed",
                    description="Azure backend is live.",
                    event_date=date.today(),
                ),
                WorkspaceActivity(user_id=user_id, action="project_updated", title="Dashboard bug fixed", project_id=project.id),
                UserUnderstanding(user_id=user_id, category="current_focus", title="Current Focus", value="Test onboarding", source="user"),
                Memory(user_id=user_id, project_id=project.id, memory_type="work", content="Payment system is working.", confidence=0.9, importance_score=0.9),
            ]
        )
        await session.flush()

        snapshot = await ContinuityModeService(session).snapshot(user)

        assert snapshot.headline == "Welcome back, Piyush."
        assert snapshot.last_focus == "Continue Synzept deployment"
        assert "Backend deployed" in snapshot.what_changed
        assert "Dashboard bug fixed" in snapshot.what_changed
        assert "Simplify product UX" in snapshot.open_loops
        assert snapshot.recommended_next_action
        assert {action.label for action in snapshot.actions} == {
            "Continue Current Work",
            "Continue Personal Goals",
            "Continue Learning",
            "Continue Recent Project",
        }
        assert snapshot.actions[-1].project_id == str(project.id)
        assert snapshot.context_used["memories"] == 1
        assert snapshot.context_used["projects"] == 1
        assert snapshot.context_used["understanding"] == 1


@pytest.mark.asyncio
async def test_continue_context_is_personal_and_contains_return_contract(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="personal-return@example.com", display_name="Ari")
        session.add_all(
            [
                user,
                UserUnderstanding(user_id=user_id, category="missions", title="Mission", value="Write a first novel", source="user"),
                UserUnderstanding(user_id=user_id, category="current_focus", title="Current Focus", value="Finish chapter three", source="user"),
            ]
        )
        await session.flush()

        context = await ContinueContextService(session).get_context(user)

        assert context.headline == "Welcome back, Ari."
        assert context.last_activity
        assert context.suggested_next_action == "Finish chapter three"
        assert context.cards[0].title == "Continue Current Focus"
        assert "Synzept" not in context.cards[0].prompt

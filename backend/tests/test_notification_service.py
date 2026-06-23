from datetime import datetime, date, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.feedback import UsageEvent
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.services.notification_service import NotificationService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'notifications.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_daily_brief_notification_text(session_factory):
    async with session_factory() as session:
        user = User(id=uuid4(), email="daily@example.com", timezone="UTC")
        session.add(user)
        await session.flush()

        candidate = NotificationService(session)._daily_brief_candidate(user)

        assert candidate.title == "Daily Brief is ready."
        assert candidate.message == "Open Synzept to review today’s most important work."
        assert candidate.metadata["href"] == "/daily-brief"


@pytest.mark.asyncio
async def test_open_loop_notification_text(session_factory):
    async with session_factory() as session:
        user_id = uuid4()
        project = Project(id=uuid4(), user_id=user_id, name="Launch")
        session.add(project)
        session.add(
            Task(
                id=uuid4(),
                user_id=user_id,
                project_id=project.id,
                title="Finish copy",
                status="pending",
            )
        )
        session.add(
            Decision(
                id=uuid4(),
                project_id=project.id,
                title="Choose launch date",
                status="pending",
            )
        )
        await session.flush()

        user = User(id=user_id, email="openloop@example.com", timezone="UTC")
        session.add(user)
        await session.flush()

        candidate = await NotificationService(session)._open_loop_candidates(user)

        assert len(candidate) == 1
        assert candidate[0].title == "Unfinished work needs your attention."
        assert candidate[0].message == "Open Synzept to review your open tasks and decisions."
        assert candidate[0].metadata["href"] == "/open-loops"


@pytest.mark.asyncio
async def test_project_attention_notifications_are_focused(session_factory):
    async with session_factory() as session:
        user_id = uuid4()
        stale_time = datetime.now(timezone.utc) - timedelta(days=10)
        project = Project(
            id=uuid4(),
            user_id=user_id,
            name="Pricing review",
            status="active",
            created_at=stale_time,
            updated_at=stale_time,
        )
        session.add(project)
        await session.flush()

        user = User(id=user_id, email="project@example.com", timezone="UTC")
        session.add(user)
        await session.flush()

        candidates = await NotificationService(session)._project_attention_candidates(user)

        assert any(item.title == "Pricing review needs attention." for item in candidates)
        assert any(item.message == "Open the project to move it forward." for item in candidates)


@pytest.mark.asyncio
async def test_return_to_work_notification_text(session_factory):
    async with session_factory() as session:
        user_id = uuid4()
        user = User(id=user_id, email="return@example.com", timezone="UTC")
        session.add(user)
        await session.flush()

        session.add(
            UsageEvent(
                id=uuid4(),
                user_id=user_id,
                event_type="daily_active",
                created_at=datetime.now(timezone.utc) - timedelta(days=4),
            )
        )
        session.add(
            Task(
                id=uuid4(),
                user_id=user_id,
                title="Review plan",
                status="pending",
            )
        )
        await session.flush()

        candidates = await NotificationService(session)._return_to_work_candidates(user)

        assert len(candidates) == 1
        assert candidates[0].title == "You have work waiting."
        assert candidates[0].message == "Open Synzept to continue where you left off."
        assert candidates[0].metadata["href"] == "/agent"


@pytest.mark.asyncio
async def test_milestone_notification_text(session_factory):
    async with session_factory() as session:
        user_id = uuid4()
        user = User(id=user_id, email="milestone@example.com", timezone="UTC")
        session.add(user)
        await session.flush()

        session.add(
            TimelineEvent(
                id=uuid4(),
                user_id=user_id,
                title="Launch plan",
                event_type="milestone",
                event_date=date.today() + timedelta(days=2),
                importance=0.8,
            )
        )
        await session.flush()

        candidates = await NotificationService(session)._milestone_candidates(user_id)

        assert len(candidates) == 1
        assert candidates[0].title == "Milestone approaching: Launch plan"
        assert candidates[0].message == "Review the milestone before it arrives."

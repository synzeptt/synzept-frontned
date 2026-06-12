from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.conversation import Conversation
from app.models.graph import GraphNode
from app.models.learning import LearningObservation, LearningSuggestion
from app.models.project import Project
from app.models.project_intelligence import ProjectDecision, ProjectOpenLoop
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.project_intelligence import ProjectDecisionCreate, ProjectOpenLoopCreate
from app.services.continuity_assistant_service import ContinuityAssistantService
from app.services.learning_engine_service import LearningEngineService
from app.services.project_intelligence_service import ProjectIntelligenceService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'assistant.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_continuity_assistant_returns_bounded_chief_of_staff_overview(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="alex@example.com", display_name="Alex")
        project = Project(user_id=user_id, name="Timeline", description="Build Timeline architecture")
        session.add_all([user, project])
        await session.flush()
        project.updated_at = datetime.now(timezone.utc) - timedelta(days=14)
        session.add_all(
            [
                UserUnderstanding(user_id=user_id, category="goals", title="Current Priorities", value="Timeline architecture\nPricing strategy\nFounder video", source="user"),
                Task(user_id=user_id, project_id=project.id, title="Finish Timeline architecture", status="todo", priority="high", due_at=datetime.now(timezone.utc) - timedelta(days=1)),
                ProjectDecision(project_id=project.id, decision="Pricing strategy", status="open"),
                ProjectOpenLoop(project_id=project.id, loop="Founder video", status="open"),
                TimelineEvent(user_id=user_id, event_type="strategy_change", title="Timeline architecture selected", description="Moved Timeline ahead of Relationship Graph.", importance=0.9, event_date=date.today()),
                Conversation(user_id=user_id, project_id=project.id, title="Timeline planning", active_intent="Finish Timeline before Relationship Graph"),
                GraphNode(user_id=user_id, node_type="project", title="AI memory Timeline"),
                GraphNode(user_id=user_id, node_type="project", title="AI memory Relationship Graph"),
            ]
        )
        await session.flush()

        overview = await ContinuityAssistantService(session).overview(user)

        assert overview.greeting == "Good morning, Alex."
        assert len(overview.priorities) <= 3
        assert len(overview.open_loops) <= 4
        assert overview.recommendation.title == "Finish Timeline architecture"
        assert "overdue" in overview.recommendation.reason
        assert overview.project_risks[0].risk == "high"
        assert overview.turning_points[0].title == "Timeline architecture selected"
        assert set(overview.hidden_connections[0].node_titles) == {"AI memory Relationship Graph", "AI memory Timeline"}


@pytest.mark.asyncio
async def test_learning_engine_explains_pattern_evidence(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="learning@example.com")
        suggestion = LearningSuggestion(user_id=user_id, title="Startup Building", description="You frequently return to startup building.", confidence=0.92, status="pending")
        session.add_all(
            [
                user,
                suggestion,
                LearningObservation(user_id=user_id, source="conversation", content="startup strategy"),
                LearningObservation(user_id=user_id, source="conversation", content="founder launch"),
                LearningObservation(user_id=user_id, source="project", content="startup roadmap"),
            ]
        )
        await session.flush()

        engine = await LearningEngineService(session).get_engine(user)

        assert engine["suggestions"][0]["evidence"] == [
            {"source": "conversation", "count": 2},
            {"source": "project", "count": 1},
        ]


@pytest.mark.asyncio
async def test_project_intelligence_surfaces_risk_reasons(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="risk@example.com"))
        project = Project(user_id=user_id, name="Pricing")
        session.add(project)
        await session.flush()
        project.updated_at = datetime.now(timezone.utc) - timedelta(days=15)
        service = ProjectIntelligenceService(session)
        await service.create_decision(user_id, project.id, ProjectDecisionCreate(decision="Choose annual pricing"))
        await service.create_loop(user_id, project.id, ProjectOpenLoopCreate(loop="Review competitor plans"))

        page = await service.get_page(user_id, project.id)

        assert page.risk.level == "high"
        assert "15 days" in page.risk.reasons[0]
        assert any("unresolved" in reason for reason in page.risk.reasons)

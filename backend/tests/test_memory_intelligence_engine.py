from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.memory.intelligence_engine import MemoryIntelligenceEngine, DecisionService, OpenLoopService
from app.models.memory import Memory
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.memory.extraction_service import ConversationTurn


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'memory-intelligence.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_decision_service_extracts_commitment_facts():
    service = DecisionService()
    turns = [ConversationTurn(role="user", content="I decided to move the launch to next week.")]

    facts = service.extract(turns)

    assert len(facts) == 1
    assert facts[0].category == "commitments"
    assert "launch" in facts[0].value


@pytest.mark.asyncio
async def test_open_loop_service_extracts_open_loop_facts():
    service = OpenLoopService()
    turns = [ConversationTurn(role="user", content="I need to follow up with the investor by Friday.")]

    facts = service.extract(turns)

    assert len(facts) == 1
    assert facts[0].category == "open_loops"
    assert "follow up" in facts[0].value.lower()


@pytest.mark.asyncio
async def test_memory_intelligence_engine_process_conversation_creates_memory_and_timeline_event(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="intelligence@example.com"))
        await session.commit()

    async with session_factory() as session:
        engine = MemoryIntelligenceEngine(session)
        result = await engine.process_conversation(
            user_id=user_id,
            turns=[
                ConversationTurn(role="user", content="My goal is to ship the continuity dashboard by Friday."),
                ConversationTurn(role="assistant", content="That sounds like a strong priority."),
                ConversationTurn(role="user", content="I need to follow up with design on the new charts."),
            ],
            conversation_id=uuid4(),
            project_id=None,
        )
        await session.commit()

        assert result.memory_count >= 1
        assert result.relationship_graph_refreshed is True
        assert result.timeline_events_created >= 0

        memories = list((await session.execute(select(Memory).where(Memory.user_id == user_id))).scalars())
        assert any("continuity dashboard" in (memory.content or "").lower() or "ship" in (memory.content or "").lower() for memory in memories)

        understanding_rows = list((await session.execute(select(UserUnderstanding).where(UserUnderstanding.user_id == user_id))).scalars())
        assert understanding_rows

        timeline_rows = list((await session.execute(select(TimelineEvent).where(TimelineEvent.user_id == user_id))).scalars())
        assert isinstance(timeline_rows, list)

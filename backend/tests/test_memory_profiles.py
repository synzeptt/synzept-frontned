from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import _ensure_local_memory_schema
from app.memory.extraction_service import ConversationTurn, MemoryExtractionService
from app.memory.memory_service import MemoryService
from app.models.memory import Memory, MemoryRevision
from app.models.user import User
from app.orchestrator.context_builder import ContextBuilder


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'memory-profile.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_extraction_finds_multiple_future_value_facts():
    extracted = await MemoryExtractionService().extract_from_conversation(
        [ConversationTurn(role="user", content="I'm building Synzept and learning AI.")]
    )

    assert [(item.memory_type, item.content) for item in extracted] == [
        ("projects", "Synzept"),
        ("interests", "AI"),
    ]


@pytest.mark.asyncio
async def test_memory_profile_persists_merges_versions_and_retrieves_by_category(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="memory@example.com", preferences={"response_depth": "concise"}))
        await session.commit()

        service = MemoryService(session)
        first = await service.process_conversation(
            user_id=user_id,
            turns=[ConversationTurn(role="user", content="I'm building Synzept and learning AI.")],
        )
        await session.commit()
        assert len(first) == 2

    async with session_factory() as session:
        service = MemoryService(session)
        merged = await service.process_conversation(
            user_id=user_id,
            turns=[ConversationTurn(role="user", content="I'm building Synzept and learning AI.")],
        )
        await session.commit()

        project = next(memory for memory in merged if memory.category == "projects")
        assert project.version == 2
        assert project.metadata_["occurrences"] == 2

        interests = await service.search_memory(user_id=user_id, category="interests")
        assert [memory.content for memory in interests] == ["AI"]

        profile = await service.get_user_profile(user_id=user_id)
        assert profile["projects"] == ["Synzept"]
        assert profile["interests"] == ["AI"]
        assert profile["preferences"] == {"response_depth": "concise"}

        revision_count = await session.scalar(
            select(func.count()).select_from(MemoryRevision).where(MemoryRevision.memory_id == project.id)
        )
        assert revision_count == 2


@pytest.mark.asyncio
async def test_context_profile_includes_durable_memory(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="context@example.com"))
        session.add(
            Memory(
                user_id=user_id,
                category="skills",
                memory_type="skills",
                content="Python",
                summary="Python",
                importance_score=0.8,
            )
        )
        await session.commit()

        profile = await ContextBuilder(session)._user_profile(user_id)

    assert "Skills: Python" in profile


@pytest.mark.asyncio
async def test_existing_sqlite_memory_table_gets_version_column(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE memories (id TEXT PRIMARY KEY)")
        await connection.run_sync(_ensure_local_memory_schema)
        columns = await connection.exec_driver_sql("PRAGMA table_info(memories)")
        assert "version" in {row[1] for row in columns}
    await engine.dispose()

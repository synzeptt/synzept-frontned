from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import _ensure_local_knows_you_schema
from app.models.user import User
from app.schemas.knows_you import LearningSuggestionCreate, LearningSuggestionEdit, UserUnderstandingBody
from app.services.knows_you_service import KnowsYouService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'knows-you.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_understanding_create_update_and_fetch_persists(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="knows-you@example.com"))
        await session.flush()

        service = KnowsYouService(session)
        created = await service.create_understanding(
            user_id,
            UserUnderstandingBody(
                personal={"name": "Piyush", "interests": "AI products"},
                professional={"role": "Founder"},
                goals={"shortTermGoals": "Ship V2"},
                preferences={"communicationStyle": "Concise"},
                learning={"topicsLearning": "Continuity systems"},
                currentFocus={"mainFocus": "Synzept Knows You"},
            ),
        )
        assert created["personal"]["name"] == "Piyush"
        assert created["currentFocus"]["mainFocus"] == "Synzept Knows You"

        updated = await service.update_understanding(
            user_id,
            UserUnderstandingBody(
                personal={"name": "Piyush", "bio": "Building Synzept"},
                professional={"role": "Lead engineer", "skills": "Product engineering"},
                goals={"longTermGoals": "Continuity OS"},
                preferences={"workStyle": "Focused blocks"},
                learning={"topicsInterestedIn": "Trustworthy AI"},
                currentFocus={"activePriorities": "Finish Phase 1"},
            ),
        )
        assert updated["personal"]["bio"] == "Building Synzept"
        assert updated["professional"]["role"] == "Lead engineer"

        fetched = await service.get_understanding(user_id)
        assert fetched["goals"]["longTermGoals"] == "Continuity OS"
        assert fetched["currentFocus"]["activePriorities"] == "Finish Phase 1"


@pytest.mark.asyncio
async def test_learning_suggestion_accept_edit_ignore_requires_user_action(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        session.add(User(id=user_id, email="suggestions@example.com"))
        await session.flush()

        service = KnowsYouService(session)
        suggestion = await service.create_suggestion(
            user_id,
            LearningSuggestionCreate(
                title="Startup projects",
                description="You frequently work on startup projects.",
            ),
        )
        assert suggestion["status"] == "pending"
        assert (await service.get_understanding(user_id))["learning"] == {}

        edited = await service.edit_suggestion(
            user_id,
            suggestion["id"],
            LearningSuggestionEdit(description="You often return to startup product work."),
        )
        assert edited["description"] == "You often return to startup product work."
        assert (await service.get_understanding(user_id))["learning"] == {}

        accepted = await service.accept_suggestion(user_id, suggestion["id"])
        assert accepted["status"] == "accepted"
        understanding = await service.get_understanding(user_id)
        assert "startup product work" in understanding["learning"]["topicsInterestedIn"]

        ignored = await service.create_suggestion(
            user_id,
            LearningSuggestionCreate(title="Concise style", description="You prefer concise responses."),
        )
        ignored = await service.ignore_suggestion(user_id, ignored["id"])
        assert ignored["status"] == "ignored"
        understanding = await service.get_understanding(user_id)
        assert "concise responses" not in understanding["learning"]["topicsInterestedIn"]


@pytest.mark.asyncio
async def test_existing_sqlite_tables_get_knows_you_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy-knows-you.db'}")
    async with engine.begin() as connection:
        await connection.exec_driver_sql("CREATE TABLE user_understanding (id TEXT PRIMARY KEY)")
        await connection.exec_driver_sql("CREATE TABLE learning_suggestions (id TEXT PRIMARY KEY)")
        await connection.run_sync(_ensure_local_knows_you_schema)
        understanding_columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(user_understanding)")}
        suggestion_columns = {row[1] for row in await connection.exec_driver_sql("PRAGMA table_info(learning_suggestions)")}
        assert {"personal", "professional", "goals", "preferences", "learning", "current_focus"} <= understanding_columns
        assert "updated_at" in suggestion_columns
    await engine.dispose()

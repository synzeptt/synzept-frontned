from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.task import Task
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.services.s1_home_service import S1HomeService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 's1-home.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_s1_home_uses_knows_you_and_active_work(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="home@example.com", display_name="Ari")
        session.add_all([
            user,
            UserUnderstanding(user_id=user_id, category="missions", title="Mission", value="Finish a first novel", source="user"),
            UserUnderstanding(user_id=user_id, category="current_focus", title="Focus", value="Write chapter three", source="user"),
            Task(user_id=user_id, title="Outline chapter four", description="Keep the story moving", priority="high", status="todo"),
        ])
        await session.flush()

        home = await S1HomeService(session).get_home(user)

        assert home.home.mission == "Finish a first novel"
        assert home.home.focus == "Write chapter three"
        assert home.home.open_loops[0].title == "Outline chapter four"
        assert home.home.suggested_next_action.title == "Outline chapter four"
        assert "Do not ask me to re-explain" in home.continue_prompt


@pytest.mark.asyncio
async def test_s1_home_has_clear_empty_state_for_new_user(session_factory):
    async with session_factory() as session:
        user = User(id=uuid4(), email="new-home@example.com")
        session.add(user)
        await session.flush()

        home = await S1HomeService(session).get_home(user)

        assert home.home.mission.startswith("Add a mission")
        assert home.home.focus.startswith("Choose the one thing")
        assert home.home.open_loops == []

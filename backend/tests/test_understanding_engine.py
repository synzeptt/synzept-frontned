from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.api.knows_you import get_user_understanding, get_user_understanding_insights, refresh_user_understanding
from app.database.base import Base
from app.models.conversation import Conversation
from app.models.memory import Memory
from app.models.message import Message
from app.models.task import Task
from app.models.user import User
from app.services.understanding_engine_service import UnderstandingEngineService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'understanding-engine.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_understanding_engine_refresh_builds_full_user_model(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="engine@example.com", display_name="Piyush")
        session.add_all(
            [
                user,
                Memory(user_id=user_id, memory_type="identity", content="My name is Piyush and I am a product founder.", summary="Piyush is a product founder.", confidence=0.9),
                Memory(user_id=user_id, memory_type="interests", content="I am interested in calm AI systems.", summary="Calm AI systems", confidence=0.82),
                Memory(user_id=user_id, memory_type="work", content="I work as founder at Synzept.", summary="Founder at Synzept", confidence=0.86),
                Memory(user_id=user_id, memory_type="goals", content="My mission is to build a personal continuity OS.", summary="Personal continuity OS", confidence=0.9),
                Memory(user_id=user_id, memory_type="priorities", content="The current priority is shipping Synzept Home.", summary="Ship Synzept Home", confidence=0.88),
                Memory(user_id=user_id, memory_type="decisions", content="We decided to keep Synzept premium and calm.", summary="Premium and calm", confidence=0.8),
                Task(user_id=user_id, title="Review understanding insights", description="Make sure next actions are clear", priority="high", status="todo"),
            ]
        )
        await session.flush()

        refreshed = await UnderstandingEngineService(session).refresh(user)

        assert refreshed.created >= 6
        assert refreshed.understanding.understandingModel.identity.background
        assert "calm AI systems" in refreshed.understanding.understandingModel.personalLife["interests"][0]
        assert refreshed.understanding.summary["whatYouCareAbout"]
        assert refreshed.understanding.summary["whatYouAreWorkingOn"]
        assert refreshed.understanding.summary["whatYouShouldDoNext"]
        assert any(insight.type == "priority" for insight in refreshed.insights)


@pytest.mark.asyncio
async def test_understanding_engine_extracts_from_recent_conversations(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="conversation-engine@example.com")
        conversation = Conversation(user_id=user_id, title="Planning")
        session.add_all([user, conversation])
        await session.flush()
        session.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content="My goal is to launch Synzept this month. I prefer concise planning and the urgent blocker is onboarding polish.",
            )
        )
        await session.flush()

        refreshed = await UnderstandingEngineService(session).refresh(user)
        model = refreshed.understanding.understandingModel

        assert model.goals["shortTermGoals"]
        assert model.personalLife["preferences"]
        assert model.currentState["currentFocus"] or model.intelligence["priorities"]
        assert refreshed.extracted > 0


@pytest.mark.asyncio
async def test_user_understanding_api_functions_return_engine_profile_and_insights(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="api-engine@example.com")
        session.add_all(
            [
                user,
                Memory(user_id=user_id, memory_type="goals", content="My goal is to finish the Synzept Understanding Engine.", summary="Finish Understanding Engine", confidence=0.9),
            ]
        )
        await session.flush()

        refresh = await refresh_user_understanding(user=user, session=session)
        profile = await get_user_understanding(user=user, session=session)
        insights = await get_user_understanding_insights(user=user, session=session)

        assert refresh.understanding.userId == user_id
        assert profile.summary["whatYouShouldDoNext"]
        assert insights

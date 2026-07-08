from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.feedback import FeedbackItem, UsageEvent
from app.models.user import User
from app.services.product_analytics_service import ProductAnalyticsService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'product-analytics.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_product_analytics_tracks_first_10_user_learning_loop(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="first@example.com")
        user.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UsageEvent(user_id=user_id, event_type="signup_completed", surface="auth"),
                UsageEvent(user_id=user_id, event_type="onboarding_first_ai_success", surface="onboarding"),
                UsageEvent(user_id=user_id, event_type="onboarding_memory_initialized", surface="onboarding"),
                UsageEvent(user_id=user_id, event_type="first_return_visit", surface="app"),
                UsageEvent(user_id=user_id, event_type="onboarding_completed", surface="onboarding"),
                UsageEvent(user_id=user_id, event_type="page_view", surface="chat"),
                UsageEvent(user_id=user_id, event_type="time_spent", surface="chat", value=120),
                FeedbackItem(user_id=user_id, feedback_type="user_interview", message="What confused you? Navigation", metadata_={"category": "Interview", "sentiment": "neutral"}),
            ]
        )
        await session.flush()

        overview = await ProductAnalyticsService(session).overview(window_days=7)

        assert overview["onboarding"]["signupCompleted"] >= 1
        assert overview["onboarding"]["firstChat"] == 1
        assert overview["onboarding"]["firstMemory"] == 1
        assert overview["onboarding"]["firstReturnVisit"] == 1
        assert overview["retention"]["returnedUsers"] == 1
        assert overview["mostUsedFeatures"][0]["feature"] == "chat"
        assert overview["mostUsedFeatures"][0]["timeSpentSeconds"] == 120
        assert overview["feedback"]["total"] == 1

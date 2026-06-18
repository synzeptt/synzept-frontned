from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.api.v1.feedback import _vote_counts, build_feedback_intelligence, classify_feedback
from app.database.base import Base
from app.models.feedback import FeedbackItem, UsageEvent
from app.models.user import User


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'feedback-intelligence.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def test_feedback_classification_detects_category_and_sentiment():
    classified = classify_feedback(
        "feature_request",
        "Please add a better Daily Brief dashboard with voting. I love the AI summary.",
        {},
    )

    assert classified["category"] == "AI"
    assert classified["sentiment"] == "positive"
    assert classified["roadmap_status"] == "new"


@pytest.mark.asyncio
async def test_feedback_intelligence_summarizes_features_issues_and_votes(session_factory):
    user_id = uuid4()
    voter_id = uuid4()
    async with session_factory() as session:
        session.add_all([User(id=user_id, email="founder@example.com"), User(id=voter_id, email="voter@example.com")])
        feature = FeedbackItem(
            user_id=user_id,
            feedback_type="feature_request",
            message="Add shared project templates for onboarding.",
            metadata_=classify_feedback("feature_request", "Add shared project templates for onboarding.", {}),
        )
        issue = FeedbackItem(
            user_id=user_id,
            feedback_type="bug",
            message="Billing checkout is slow and confusing.",
            metadata_=classify_feedback("bug", "Billing checkout is slow and confusing.", {}),
        )
        compliment = FeedbackItem(
            user_id=voter_id,
            feedback_type="general",
            message="The memory system is useful and clear.",
            metadata_=classify_feedback("general", "The memory system is useful and clear.", {}),
        )
        session.add_all([feature, issue, compliment])
        await session.flush()
        session.add(UsageEvent(user_id=voter_id, event_type="feedback_feature_voted", surface="feedback", metadata_={"feedback_id": str(feature.id)}))
        await session.flush()

        votes = await _vote_counts(session)
        intelligence = build_feedback_intelligence([feature, issue, compliment], votes)

        assert votes[str(feature.id)] == 1
        assert intelligence["total"] == 3
        assert intelligence["most_requested_features"][0].id == feature.id
        assert intelligence["most_requested_features"][0].votes == 1
        assert intelligence["top_reported_issues"][0].category == "Billing"
        assert intelligence["most_common_compliments"][0].sentiment == "positive"
        assert intelligence["product_insights"]["what_should_be_prioritized"]

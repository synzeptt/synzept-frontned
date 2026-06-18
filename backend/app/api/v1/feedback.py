from collections import Counter, defaultdict
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import bearer_scheme, get_current_user, get_db
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.security import decode_token
from app.models.feedback import FeedbackItem, MemoryFeedback, UsageEvent
from app.models.user import User
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackIntelligenceOut,
    FeedbackOut,
    FeedbackSignal,
    FeedbackStatusUpdate,
    FeatureRequestOut,
    MemoryFeedbackCreate,
    UsageEventCreate,
    UsefulnessMetrics,
)

router = APIRouter(prefix="/feedback")
analytics_router = APIRouter(prefix="/analytics")

FEEDBACK_CATEGORIES = ("UI/UX", "AI", "Memory", "Projects", "Dashboard", "Performance", "Billing")
STATUS_VALUES = {"new", "planned", "in_progress", "shipped", "closed"}

CATEGORY_KEYWORDS = {
    "Billing": ("billing", "payment", "razorpay", "checkout", "invoice", "subscription", "plan", "price", "upgrade"),
    "Memory": ("memory", "remember", "forgot", "recall", "context", "knows me", "understands"),
    "AI": ("ai", "agent", "chat", "response", "answer", "model", "prompt", "assistant"),
    "Projects": ("project", "task", "goal", "milestone", "timeline", "open loop", "decision"),
    "Dashboard": ("dashboard", "daily brief", "weekly", "personal os", "home", "brief"),
    "Performance": ("slow", "lag", "loading", "performance", "timeout", "crash", "freeze", "buggy"),
    "UI/UX": ("ui", "ux", "design", "mobile", "button", "navigation", "screen", "layout", "confusing", "hard to use"),
}

POSITIVE_WORDS = ("love", "great", "useful", "helpful", "clear", "fast", "beautiful", "excellent", "good", "works")
NEGATIVE_WORDS = ("bug", "broken", "slow", "confusing", "bad", "wrong", "frustrating", "annoying", "failed", "issue", "error")


@router.post("", response_model=FeedbackOut)
async def create_feedback(
    body: FeedbackCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    classification = classify_feedback(body.feedback_type, body.message or "", body.metadata)
    item = FeedbackItem(
        user_id=user.id,
        feedback_type=body.feedback_type,
        message=body.message,
        rating=body.rating,
        conversation_id=body.conversation_id,
        message_id=body.message_id,
        memory_id=body.memory_id,
        metadata_={**body.metadata, **classification},
    )
    session.add(item)
    session.add(
        UsageEvent(
            user_id=user.id,
            event_type="feedback_submitted",
            surface="feedback",
            metadata_={
                "feedback_type": body.feedback_type,
                "category": classification["category"],
                "sentiment": classification["sentiment"],
            },
        )
    )
    await session.flush()
    return item


@router.get("/intelligence", response_model=FeedbackIntelligenceOut)
async def feedback_intelligence(
    window_days: int = 90,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    require_feedback_admin(user)
    since = date.today() - timedelta(days=min(max(window_days, 7), 365))
    feedback = await _feedback_since(session, since)
    votes = await _vote_counts(session)
    return build_feedback_intelligence(feedback, votes)


@router.get("/features", response_model=list[FeatureRequestOut])
async def feature_requests(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(FeedbackItem)
        .where(FeedbackItem.feedback_type.in_(("feature_request", "suggestion", "improvement")))
        .order_by(FeedbackItem.created_at.desc())
        .limit(100)
    )
    rows = list(result.scalars())
    votes = await _vote_counts(session)
    user_votes = await _user_votes(session, user.id)
    return [feature_out(item, votes.get(str(item.id), 0), str(item.id) in user_votes) for item in rows]


@router.post("/{feedback_id}/vote")
async def vote_feedback(
    feedback_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    item = await session.get(FeedbackItem, feedback_id)
    if not item or item.feedback_type not in {"feature_request", "suggestion", "improvement"}:
        raise NotFoundError("Feature request not found")
    existing = await session.execute(
        select(UsageEvent).where(
            UsageEvent.user_id == user.id,
            UsageEvent.event_type == "feedback_feature_voted",
            UsageEvent.metadata_["feedback_id"].as_string() == str(feedback_id),
        )
    )
    if not existing.scalar_one_or_none():
        session.add(
            UsageEvent(
                user_id=user.id,
                event_type="feedback_feature_voted",
                surface="feedback",
                metadata_={"feedback_id": str(feedback_id), "category": feedback_category(item)},
            )
        )
        await session.flush()
    votes = await _vote_counts(session)
    return {"ok": True, "votes": votes.get(str(feedback_id), 0)}


@router.patch("/{feedback_id}/status", response_model=FeatureRequestOut)
async def update_feedback_status(
    feedback_id: UUID,
    body: FeedbackStatusUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    require_feedback_admin(user)
    item = await session.get(FeedbackItem, feedback_id)
    if not item:
        raise NotFoundError("Feedback not found")
    item.status = body.status
    item.metadata_ = {**(item.metadata_ or {}), "roadmap_status": body.status}
    await session.flush()
    votes = await _vote_counts(session)
    return feature_out(item, votes.get(str(item.id), 0), False)


@router.post("/memory")
async def create_memory_feedback(
    body: MemoryFeedbackCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    item = MemoryFeedback(
        user_id=user.id,
        memory_id=body.memory_id,
        signal=body.signal,
        rating=body.rating,
        corrected_context=body.corrected_context,
        metadata_=body.metadata,
    )
    session.add(item)
    await session.flush()
    return {"ok": True, "id": item.id}


def require_feedback_admin(user: User) -> None:
    if not user.email:
        raise UnauthorizedError("Founder feedback access required")
    # Keep this permissive in local/staging while still protecting production through the founder analytics setting.
    from app.core.config import get_settings

    settings = get_settings()
    allowed = settings.founder_analytics_email_list
    if allowed and user.email.lower() not in allowed:
        raise UnauthorizedError("Founder feedback access required")
    if settings.environment == "production" and not allowed:
        raise UnauthorizedError("Founder feedback access required")


def classify_feedback(feedback_type: str, message: str, metadata: dict | None = None) -> dict:
    text = f"{message} {' '.join(str(value) for value in (metadata or {}).values())}".casefold()
    category = next(
        (
            name
            for name, keywords in CATEGORY_KEYWORDS.items()
            if any(keyword in text for keyword in keywords)
        ),
        "UI/UX",
    )
    if feedback_type == "memory_issue":
        category = "Memory"
    if feedback_type == "user_interview":
        category = "Interview"
    if feedback_type == "bug" and category == "UI/UX":
        category = "Performance" if any(word in text for word in CATEGORY_KEYWORDS["Performance"]) else "UI/UX"
    sentiment_score = sum(word in text for word in POSITIVE_WORDS) - sum(word in text for word in NEGATIVE_WORDS)
    sentiment = "positive" if sentiment_score > 0 else "negative" if sentiment_score < 0 or feedback_type in {"issue", "bug", "memory_issue"} else "neutral"
    title = title_from_message(message, fallback=label_for_type(feedback_type))
    return {
        "category": category,
        "sentiment": sentiment,
        "summary": title,
        "roadmap_status": (metadata or {}).get("roadmap_status", "new"),
    }


async def _feedback_since(session: AsyncSession, since: date) -> list[FeedbackItem]:
    result = await session.execute(
        select(FeedbackItem)
        .where(func.date(FeedbackItem.created_at) >= since.isoformat())
        .order_by(FeedbackItem.created_at.desc())
        .limit(500)
    )
    return list(result.scalars())


async def _vote_counts(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(
        select(
            UsageEvent.metadata_["feedback_id"].as_string().label("feedback_id"),
            func.count(distinct(UsageEvent.user_id)),
        )
        .where(UsageEvent.event_type == "feedback_feature_voted")
        .group_by(UsageEvent.metadata_["feedback_id"].as_string())
    )
    return {str(feedback_id): int(count or 0) for feedback_id, count in result.all() if feedback_id}


async def _user_votes(session: AsyncSession, user_id: UUID) -> set[str]:
    result = await session.execute(
        select(UsageEvent.metadata_["feedback_id"].as_string()).where(
            UsageEvent.user_id == user_id,
            UsageEvent.event_type == "feedback_feature_voted",
        )
    )
    return {str(value) for value in result.scalars() if value}


def build_feedback_intelligence(feedback: list[FeedbackItem], votes: dict[str, int]) -> dict:
    categories = Counter(feedback_category(item) for item in feedback)
    sentiments = Counter(feedback_sentiment(item) for item in feedback)
    feature_rows = [item for item in feedback if item.feedback_type in {"feature_request", "suggestion", "improvement"}]
    issue_rows = [item for item in feedback if feedback_sentiment(item) == "negative" or item.feedback_type in {"issue", "bug", "memory_issue"}]
    compliment_rows = [item for item in feedback if feedback_sentiment(item) == "positive"]
    trend_rows = top_trends(feedback, votes)
    sentiment_score = sentiments["positive"] - sentiments["negative"]
    return {
        "total": len(feedback),
        "user_sentiment": "positive" if sentiment_score > 0 else "negative" if sentiment_score < 0 else "neutral",
        "sentiment_score": sentiment_score,
        "categories": [{"category": category, "count": count} for category, count in categories.most_common()],
        "most_requested_features": [signal(item, votes) for item in sorted(feature_rows, key=lambda item: demand_score(item, votes), reverse=True)[:8]],
        "most_common_frustrations": [signal(item, votes) for item in sorted(issue_rows, key=lambda item: demand_score(item, votes), reverse=True)[:8]],
        "most_common_compliments": [signal(item, votes) for item in compliment_rows[:8]],
        "emerging_trends": trend_rows[:8],
        "top_reported_issues": [signal(item, votes) for item in sorted(issue_rows, key=lambda item: item.created_at, reverse=True)[:8]],
        "product_insights": weekly_report(feedback, votes),
    }


def top_trends(feedback: list[FeedbackItem], votes: dict[str, int]) -> list[dict]:
    grouped: dict[str, list[FeedbackItem]] = defaultdict(list)
    for item in feedback:
        grouped[feedback_category(item)].append(item)
    trends = []
    for category, rows in grouped.items():
        total_votes = sum(votes.get(str(item.id), 0) for item in rows)
        detail = f"{len(rows)} feedback item{'s' if len(rows) != 1 else ''}, {total_votes} vote{'s' if total_votes != 1 else ''}."
        trends.append(
            FeedbackSignal(
                id=None,
                title=f"{category} demand",
                detail=detail,
                category=category,
                feedback_type="trend",
                sentiment=dominant_sentiment(rows),
                status="new",
                votes=total_votes,
                demand_score=len(rows) * 2 + total_votes,
            ).model_dump()
        )
    return sorted(trends, key=lambda item: item["demand_score"], reverse=True)


def weekly_report(feedback: list[FeedbackItem], votes: dict[str, int]) -> dict:
    requested = [signal(item, votes).model_dump() for item in feedback if item.feedback_type in {"feature_request", "suggestion", "improvement"}]
    dislikes = [signal(item, votes).model_dump() for item in feedback if feedback_sentiment(item) == "negative"]
    compliments = [signal(item, votes).model_dump() for item in feedback if feedback_sentiment(item) == "positive"]
    priorities = sorted([*requested, *dislikes], key=lambda item: item["demand_score"], reverse=True)[:5]
    return {
        "what_users_want": requested[:5],
        "what_users_dislike": dislikes[:5],
        "what_users_like": compliments[:5],
        "what_should_be_prioritized": priorities,
    }


def signal(item: FeedbackItem, votes: dict[str, int]) -> FeedbackSignal:
    vote_count = votes.get(str(item.id), 0)
    return FeedbackSignal(
        id=item.id,
        title=str((item.metadata_ or {}).get("summary") or title_from_message(item.message or "", fallback=label_for_type(item.feedback_type))),
        detail=item.message or "",
        category=feedback_category(item),
        feedback_type=item.feedback_type,
        sentiment=feedback_sentiment(item),
        status=str((item.metadata_ or {}).get("roadmap_status") or item.status or "new"),
        votes=vote_count,
        demand_score=demand_score(item, votes),
        created_at=item.created_at,
    )


def feature_out(item: FeedbackItem, votes: int, user_voted: bool) -> FeatureRequestOut:
    return FeatureRequestOut(
        id=item.id,
        title=str((item.metadata_ or {}).get("summary") or title_from_message(item.message or "", fallback=label_for_type(item.feedback_type))),
        detail=item.message or "",
        category=feedback_category(item),
        status=str((item.metadata_ or {}).get("roadmap_status") or item.status or "new"),
        votes=votes,
        user_voted=user_voted,
        demand_score=demand_score(item, {str(item.id): votes}),
        created_at=item.created_at,
    )


def demand_score(item: FeedbackItem, votes: dict[str, int]) -> int:
    type_weight = 3 if item.feedback_type in {"feature_request", "suggestion", "improvement"} else 2 if item.feedback_type in {"bug", "issue", "memory_issue"} else 1
    sentiment_weight = 2 if feedback_sentiment(item) == "negative" else 1
    return type_weight + sentiment_weight + votes.get(str(item.id), 0) * 3


def feedback_category(item: FeedbackItem) -> str:
    return str((item.metadata_ or {}).get("category") or "UI/UX")


def feedback_sentiment(item: FeedbackItem) -> str:
    return str((item.metadata_ or {}).get("sentiment") or "neutral")


def dominant_sentiment(rows: list[FeedbackItem]) -> str:
    counts = Counter(feedback_sentiment(item) for item in rows)
    return counts.most_common(1)[0][0] if counts else "neutral"


def title_from_message(message: str, fallback: str) -> str:
    clean = " ".join((message or "").strip().split())
    if not clean:
        return fallback
    sentence = clean.split(".")[0].strip()
    return sentence[:90] or fallback


def label_for_type(feedback_type: str) -> str:
    return {
        "bug": "Bug report",
        "issue": "Reported issue",
        "feature_request": "Feature request",
        "improvement": "Improvement",
        "suggestion": "Suggestion",
        "general": "General feedback",
        "memory_issue": "Memory feedback",
        "support": "Support request",
        "user_interview": "User interview",
    }.get(feedback_type, "Feedback")


@analytics_router.post("/event")
async def create_usage_event(
    body: UsageEventCreate,
    credentials: HTTPAuthorizationCredentials | User | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
):
    user_id = None
    if isinstance(credentials, User):
        user_id = credentials.id
    elif credentials and credentials.credentials:
        try:
            payload = decode_token(credentials.credentials, "access")
            candidate_user_id = UUID(payload["sub"])
            result = await session.execute(
                select(User.id).where(
                    User.id == candidate_user_id,
                    User.deleted_at.is_(None),
                    User.is_active.is_(True),
                )
            )
            user_id = result.scalar_one_or_none()
        except Exception:
            return {"ok": False}

    if user_id is None:
        return {"ok": True}

    event = UsageEvent(
        user_id=user_id,
        event_type=body.event_type,
        surface=body.surface,
        value=body.value,
        metadata_=body.metadata,
    )
    try:
        session.add(event)
        await session.flush()
        return {"ok": True}
    except Exception:
        return {"ok": False}


@analytics_router.get("/usefulness", response_model=UsefulnessMetrics)
async def usefulness_metrics(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    since = date.today() - timedelta(days=30)

    async def count_events(*event_types: str) -> int:
        result = await session.execute(
            select(func.count(UsageEvent.id)).where(
                UsageEvent.user_id == user.id,
                UsageEvent.event_type.in_(event_types),
                UsageEvent.created_at >= since,
            )
        )
        return int(result.scalar() or 0)

    active_days = await session.execute(
        select(func.count(distinct(func.date(UsageEvent.created_at)))).where(
            UsageEvent.user_id == user.id,
            UsageEvent.event_type == "daily_active",
            UsageEvent.created_at >= since,
        )
    )
    feedback_count = await session.execute(
        select(func.count(FeedbackItem.id)).where(FeedbackItem.user_id == user.id, FeedbackItem.created_at >= since)
    )
    avg_rating = await session.execute(
        select(func.avg(FeedbackItem.rating)).where(
            FeedbackItem.user_id == user.id,
            FeedbackItem.feedback_type == "response_rating",
            FeedbackItem.rating.is_not(None),
            FeedbackItem.created_at >= since,
        )
    )

    average_response_rating = avg_rating.scalar()

    return UsefulnessMetrics(
        daily_active_days=int(active_days.scalar() or 0),
        conversations_started=await count_events("conversation_started"),
        messages_sent=await count_events("message_sent"),
        memory_events=await count_events("memory_retrieved", "memory_created", "memory_edited", "memory_removed"),
        project_events=await count_events("project_opened", "project_created", "project_continued"),
        task_events=await count_events("task_created", "task_completed", "task_continued"),
        onboarding_events=await count_events("onboarding_started", "onboarding_completed"),
        dashboard_returns=await count_events("dashboard_loaded", "returning_dashboard_loaded"),
        continuation_cards_opened=await count_events("continuity_card_opened"),
        restoration_actions=await count_events("continuity_card_opened", "project_continued", "task_continued", "conversation_continued"),
        feedback_items=int(feedback_count.scalar() or 0),
        average_response_rating=float(average_response_rating) if average_response_rating is not None else None,
    )

from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import bearer_scheme, get_current_user, get_db
from app.core.security import decode_token
from app.models.feedback import FeedbackItem, MemoryFeedback, UsageEvent
from app.models.user import User
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackOut,
    MemoryFeedbackCreate,
    UsageEventCreate,
    UsefulnessMetrics,
)

router = APIRouter(prefix="/feedback")
analytics_router = APIRouter(prefix="/analytics")


@router.post("", response_model=FeedbackOut)
async def create_feedback(
    body: FeedbackCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    item = FeedbackItem(
        user_id=user.id,
        feedback_type=body.feedback_type,
        message=body.message,
        rating=body.rating,
        conversation_id=body.conversation_id,
        message_id=body.message_id,
        memory_id=body.memory_id,
        metadata_=body.metadata,
    )
    session.add(item)
    await session.flush()
    return item


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

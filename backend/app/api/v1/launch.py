import secrets
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import UnauthorizedError
from app.models.feedback import FeedbackItem, UsageEvent
from app.models.launch import InviteCode, WaitlistEntry
from app.models.user import User
from app.schemas.launch import AccessStatus, FirstUsersLaunchOut, InviteCreate, InviteOut, WaitlistJoin, WaitlistOut

router = APIRouter(prefix="/launch")


@router.get("/access", response_model=AccessStatus)
async def access_status():
    settings = get_settings()
    return AccessStatus(
        early_access_enabled=settings.early_access_enabled,
        invite_required=settings.invite_required,
    )


@router.post("/waitlist", response_model=WaitlistOut)
async def join_waitlist(body: WaitlistJoin, session: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    result = await session.execute(select(WaitlistEntry).where(WaitlistEntry.email == email))
    entry = result.scalar_one_or_none()
    if entry:
        entry.name = body.name or entry.name
        entry.role = body.role or entry.role
        entry.intended_use = body.intended_use or entry.intended_use
        entry.source = body.source or entry.source
        return entry

    entry = WaitlistEntry(
        email=email,
        name=body.name,
        role=body.role,
        intended_use=body.intended_use,
        source=body.source,
    )
    session.add(entry)
    await session.flush()
    return entry


@router.post("/invites", response_model=InviteOut)
async def create_invite(
    body: InviteCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    require_launch_admin(user)
    invite = InviteCode(
        code=secrets.token_urlsafe(12),
        email=body.email.lower() if body.email else None,
        max_uses=body.max_uses,
        notes=body.notes,
        created_by_user_id=user.id,
    )
    session.add(invite)
    await session.flush()
    return invite


@router.get("/invites", response_model=list[InviteOut])
async def list_invites(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    require_launch_admin(user)
    result = await session.execute(select(InviteCode).order_by(InviteCode.created_at.desc()).limit(100))
    return list(result.scalars())


@router.get("/first-users", response_model=FirstUsersLaunchOut)
async def first_users_launch(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    require_launch_admin(user)
    settings = get_settings()
    invite_result = await session.execute(select(InviteCode).order_by(InviteCode.created_at.desc()).limit(100))
    invites = list(invite_result.scalars())
    founder_emails = [email.lower() for email in settings.founder_analytics_email_list]
    users_query = select(User).where(User.deleted_at.is_(None))
    if founder_emails:
        users_query = users_query.where(User.email.not_in(founder_emails))
    users_result = await session.execute(users_query.order_by(User.created_at.asc()).limit(10))
    first_users = list(users_result.scalars())
    user_ids = [row.id for row in first_users]
    today = date.today()
    since = today - timedelta(days=30)

    event_counts: dict = defaultdict(int)
    last_activity: dict = {}
    active_user_ids: set = set()
    if user_ids:
        event_rows = await session.execute(
            select(UsageEvent.user_id, func.count(UsageEvent.id), func.max(UsageEvent.created_at))
            .where(UsageEvent.user_id.in_(user_ids))
            .group_by(UsageEvent.user_id)
        )
        for user_id, count, latest in event_rows.all():
            event_counts[user_id] = int(count or 0)
            last_activity[user_id] = latest

        active_rows = await session.execute(
            select(distinct(UsageEvent.user_id)).where(
                UsageEvent.user_id.in_(user_ids),
                UsageEvent.event_type.in_(("daily_active", "dashboard_loaded", "page_view", "chat_message_sent", "message_sent")),
                func.date(UsageEvent.created_at) >= since.isoformat(),
            )
        )
        active_user_ids = {value for value in active_rows.scalars() if value}

    feedback_counts: dict = defaultdict(int)
    user_feedback = []
    if user_ids:
        feedback_rows = await session.execute(
            select(FeedbackItem).where(FeedbackItem.user_id.in_(user_ids)).order_by(FeedbackItem.created_at.desc())
        )
        feedback_items = list(feedback_rows.scalars())
        for item in feedback_items:
            feedback_counts[item.user_id] += 1

        interview_rows = await session.execute(
            select(FeedbackItem).where(FeedbackItem.feedback_type == "user_interview").order_by(FeedbackItem.created_at.desc()).limit(200)
        )
        user_feedback = list(interview_rows.scalars())

    interview_by_email = {}
    for item in user_feedback:
        email = str((item.metadata_ or {}).get("target_user_email") or "").lower()
        if email and email not in interview_by_email:
            interview_by_email[email] = item

    session_rows = []
    for row in first_users:
        interview = interview_by_email.get(row.email.lower())
        metadata = interview.metadata_ if interview else {}
        session_rows.append(
            {
                "user_id": row.id,
                "email": row.email,
                "display_name": row.display_name,
                "onboarding_state": row.onboarding_state,
                "created_at": row.created_at,
                "last_activity_at": last_activity.get(row.id),
                "session_events": event_counts[row.id],
                "feedback_items": feedback_counts[row.id],
                "interview_completed": bool(interview),
                "confusing_moments": _clean_list(metadata.get("confusing_moments") if metadata else []),
                "exciting_moments": _clean_list(metadata.get("exciting_moments") if metadata else []),
                "drop_off_points": _clean_list(metadata.get("drop_off_points") if metadata else []),
                "tomorrow_answer": metadata.get("come_back_tomorrow") if metadata else None,
            }
        )

    sessions_watched = sum(1 for row in session_rows if row["confusing_moments"] or row["exciting_moments"] or row["drop_off_points"])
    return FirstUsersLaunchOut(
        target_users=10,
        invited_users=len(invites),
        accepted_invites=sum(invite.use_count for invite in invites),
        signed_up_users=len(first_users),
        active_users=len(active_user_ids),
        completed_onboarding=sum(1 for row in first_users if row.onboarding_state == "complete"),
        interviews_completed=sum(1 for row in session_rows if row["interview_completed"]),
        sessions_watched=sessions_watched,
        invite_url_base=f"{settings.frontend_url.rstrip('/')}/signup",
        invites=invites,
        first_users=session_rows,
    )


def require_launch_admin(user: User) -> None:
    settings = get_settings()
    allowed = settings.founder_analytics_email_list
    if allowed and user.email.lower() not in allowed:
        raise UnauthorizedError("Launch access required")
    if settings.environment == "production" and not allowed:
        raise UnauthorizedError("Launch access required")


def _clean_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()][:5]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []

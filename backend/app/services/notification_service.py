from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.feedback import UsageEvent
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_intelligence_phase2 import Decision, OpenLoop
from app.models.task import Task
from app.models.timeline_event import TimelineEvent
from app.models.user import User
from app.schemas.notifications import NotificationSettingsUpdate
from app.services.email_service import EmailService

OPEN_TASK_STATUSES = {"todo", "pending", "in_progress"}


@dataclass
class NotificationCandidate:
    notification_type: str
    title: str
    message: str
    priority: str
    dedupe_key: str
    metadata: dict


class NotificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def overview(self, user: User, *, generate: bool = False) -> dict:
        generated = await self.generate_for_user(user) if generate else 0
        rows = await self._notifications(user.id)
        unread = sum(1 for row in rows if not row.read_at)
        return {
            "settings": self.notification_settings(user),
            "notifications": [self._out(row) for row in rows],
            "generated": generated,
            "unread": unread,
        }

    async def update_settings(self, user: User, body: NotificationSettingsUpdate) -> dict:
        prefs = dict(user.preferences or {})
        current = self.notification_settings(user)
        merged = current | {k: v for k, v in body.model_dump(exclude_none=True).items()}
        prefs["notifications"] = self._normalize_settings(merged)
        user.preferences = prefs
        await self.session.flush()
        return self.notification_settings(user)

    async def mark_read(self, user: User, notification_id: UUID) -> dict:
        result = await self.session.execute(
            select(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
        )
        notification = result.scalar_one_or_none()
        if notification:
            notification.read_at = datetime.now(timezone.utc)
            notification.status = "read"
            await self.session.flush()
        return await self.overview(user)

    async def generate_for_user(self, user: User) -> int:
        settings = self.notification_settings(user)
        if not settings["enabled"] or settings["frequency"] == "off":
            return 0
        if settings["frequency"] == "weekdays" and self._local_now(user).weekday() >= 5:
            return 0

        candidates: list[NotificationCandidate] = []
        if settings["dailyBrief"] and self._can_send_daily(settings, user):
            candidates.append(self._daily_brief_candidate(user))
        if settings["openLoops"]:
            candidates.extend(await self._open_loop_candidates(user))
        if settings["projectAttention"]:
            candidates.extend(await self._project_attention_candidates(user))
        if settings["returnToWork"]:
            candidates.extend(await self._return_to_work_candidates(user))
        if settings["frequency"] == "important_only":
            candidates = [item for item in candidates if item.priority == "high"]

        created = 0
        for candidate in candidates:
            if await self._create_notification(user, candidate, settings):
                created += 1
        return created

    async def generate_for_all_users(self) -> int:
        result = await self.session.execute(select(User).where(User.deleted_at.is_(None), User.is_active.is_(True)))
        total = 0
        for user in result.scalars():
            total += await self.generate_for_user(user)
        return total

    def notification_settings(self, user: User) -> dict:
        raw = dict((user.preferences or {}).get("notifications") or {})
        return self._normalize_settings(raw)

    def _normalize_settings(self, raw: dict) -> dict:
        frequency = raw.get("frequency", "daily")
        if frequency not in {"daily", "weekdays", "important_only", "off"}:
            frequency = "daily"
        morning_time = raw.get("morningTime") or raw.get("morning_time") or "09:00"
        if not isinstance(morning_time, str) or len(morning_time) != 5:
            morning_time = "09:00"
        return {
            "enabled": raw.get("enabled", True),
            "dailyBrief": raw.get("dailyBrief", True),
            "openLoops": raw.get("openLoops", True),
            "projectAttention": raw.get("projectAttention", True),
            "returnToWork": raw.get("returnToWork", True),
            "email": raw.get("email", False),
            "push": raw.get("push", False),
            "frequency": frequency,
            "morningTime": morning_time,
        }

    async def _notifications(self, user_id: UUID) -> list[Notification]:
        result = await self.session.execute(
            select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc()).limit(40)
        )
        return list(result.scalars())

    def _daily_brief_candidate(self, user: User) -> NotificationCandidate:
        day = self._local_now(user).date().isoformat()
        return NotificationCandidate(
            notification_type="daily_brief",
            title="Your Daily Brief is ready.",
            message="Your Daily Brief is ready. Open Synzept to see what matters, what is unfinished, and what to do next.",
            priority="medium",
            dedupe_key=f"daily_brief:{day}",
            metadata={"href": "/daily-brief"},
        )

    async def _open_loop_candidates(self, user: User) -> list[NotificationCandidate]:
        day = self._local_now(user).date().isoformat()
        open_task_count = await self._count_open_tasks(user.id)
        pending_decision_count = await self._count_pending_decisions(user.id)
        overdue_followups = await self._count_overdue_followups(user.id)
        total = open_task_count + pending_decision_count + overdue_followups
        if not total:
            return []
        priority = "high" if pending_decision_count or overdue_followups else "medium"
        detail = []
        if open_task_count:
            detail.append(f"{open_task_count} unfinished task{'s' if open_task_count != 1 else ''}")
        if pending_decision_count:
            detail.append(f"{pending_decision_count} pending decision{'s' if pending_decision_count != 1 else ''}")
        if overdue_followups:
            detail.append(f"{overdue_followups} overdue follow-up{'s' if overdue_followups != 1 else ''}")
        return [
            NotificationCandidate(
                notification_type="open_loop",
                title="Important unfinished work needs attention.",
                message=f"You have {', '.join(detail)} waiting in Synzept.",
                priority=priority,
                dedupe_key=f"open_loops:{day}:{total}",
                metadata={"href": "/open-loops", "openTasks": open_task_count, "pendingDecisions": pending_decision_count, "overdueFollowups": overdue_followups},
            )
        ]

    async def _project_attention_candidates(self, user: User) -> list[NotificationCandidate]:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(Project).where(Project.user_id == user.id, Project.deleted_at.is_(None), Project.status.not_in(("archived", "completed"))).limit(50)
        )
        candidates: list[NotificationCandidate] = []
        for project in result.scalars():
            updated = self._as_utc(project.updated_at or project.created_at)
            inactive_days = (now - updated).days if updated else 0
            if inactive_days >= 7:
                candidates.append(
                    NotificationCandidate(
                        notification_type="project_attention",
                        title=f"{project.name} needs attention.",
                        message=f"{project.name} has had no activity for {inactive_days} days.",
                        priority="high" if inactive_days >= 14 else "medium",
                        dedupe_key=f"project_inactive:{project.id}:{inactive_days // 7}",
                        metadata={"href": f"/projects/{project.id}", "projectId": str(project.id), "inactiveDays": inactive_days},
                    )
                )
            if "blocked" in (project.status or "").lower() or "blocked" in (project.current_focus or "").lower():
                candidates.append(
                    NotificationCandidate(
                        notification_type="project_attention",
                        title=f"{project.name} may be blocked.",
                        message=f"{project.name} looks blocked. Open it to decide the next step.",
                        priority="high",
                        dedupe_key=f"project_blocked:{project.id}",
                        metadata={"href": f"/projects/{project.id}", "projectId": str(project.id)},
                    )
                )
        milestone_candidates = await self._milestone_candidates(user.id)
        return [*candidates, *milestone_candidates]

    async def _return_to_work_candidates(self, user: User) -> list[NotificationCandidate]:
        last_seen = await self._last_seen(user.id)
        if not last_seen:
            return []
        days = (datetime.now(timezone.utc) - self._as_utc(last_seen)).days
        threshold = 14 if days >= 14 else 7 if days >= 7 else 3 if days >= 3 else 0
        if not threshold:
            return []
        unfinished = await self._count_open_tasks(user.id)
        open_loops = await self._count_open_loops(user.id)
        if not unfinished and not open_loops:
            return []
        return [
            NotificationCandidate(
                notification_type="return_to_work",
                title="You have unfinished work waiting in Synzept.",
                message="You have unfinished work waiting in Synzept. Open your workspace to continue where you left off.",
                priority="high" if threshold >= 7 else "medium",
                dedupe_key=f"return_to_work:{threshold}:{last_seen.date().isoformat()}",
                metadata={"href": "/agent", "daysInactive": days, "unfinished": unfinished, "openLoops": open_loops},
            )
        ]

    async def _milestone_candidates(self, user_id: UUID) -> list[NotificationCandidate]:
        today = datetime.now(timezone.utc).date()
        result = await self.session.execute(
            select(TimelineEvent).where(
                TimelineEvent.user_id == user_id,
                TimelineEvent.event_type == "milestone",
                TimelineEvent.event_date >= today,
                TimelineEvent.event_date <= today + timedelta(days=3),
            )
        )
        candidates = []
        for event in result.scalars():
            candidates.append(
                NotificationCandidate(
                    notification_type="project_attention",
                    title=f"Milestone approaching: {event.title}",
                    message=f"{event.title} is approaching. Review the related project and next step.",
                    priority="high" if event.importance >= 0.75 else "medium",
                    dedupe_key=f"milestone_due:{event.id}:{event.event_date.isoformat()}",
                    metadata={"href": f"/projects/{event.project_id}" if event.project_id else "/timeline", "eventId": str(event.id)},
                )
            )
        return candidates

    async def _create_notification(self, user: User, candidate: NotificationCandidate, settings: dict) -> bool:
        existing = await self.session.execute(
            select(Notification.id).where(Notification.user_id == user.id, Notification.dedupe_key == candidate.dedupe_key).limit(1)
        )
        if existing.scalar_one_or_none():
            return False
        notification = Notification(
            user_id=user.id,
            notification_type=candidate.notification_type,
            channel="email" if settings["email"] else "push" if settings["push"] else "in_app",
            title=candidate.title,
            message=candidate.message,
            priority=candidate.priority,
            dedupe_key=candidate.dedupe_key,
            scheduled_for=datetime.now(timezone.utc),
            metadata_=candidate.metadata,
        )
        self.session.add(notification)
        await self.session.flush()

        if settings["email"]:
            try:
                EmailService().send_notification(
                    email=user.email,
                    subject=candidate.title,
                    message=candidate.message,
                    action_url=f"{self.settings.frontend_url.rstrip('/')}{candidate.metadata.get('href', '/agent')}",
                )
                notification.status = "sent"
                notification.sent_at = datetime.now(timezone.utc)
            except Exception:
                notification.status = "pending"
        await self.session.flush()
        return True

    def _can_send_daily(self, settings: dict, user: User) -> bool:
        now = self._local_now(user)
        try:
            hour, minute = [int(part) for part in settings["morningTime"].split(":", 1)]
        except ValueError:
            hour, minute = 9, 0
        return now.time() >= time(hour, minute)

    async def _count_open_tasks(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None), Task.status.in_(OPEN_TASK_STATUSES))
        )
        return int(result.scalar() or 0)

    async def _count_open_loops(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(OpenLoop)
            .join(Project, Project.id == OpenLoop.project_id)
            .where(Project.user_id == user_id, OpenLoop.status == "open")
        )
        return int(result.scalar() or 0)

    async def _count_pending_decisions(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Decision)
            .join(Project, Project.id == Decision.project_id)
            .where(Project.user_id == user_id, Decision.status == "pending")
        )
        return int(result.scalar() or 0)

    async def _count_overdue_followups(self, user_id: UUID) -> int:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(func.count()).select_from(Task).where(
                Task.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_at.is_not(None),
                Task.due_at < now,
            )
        )
        return int(result.scalar() or 0)

    async def _last_seen(self, user_id: UUID) -> datetime | None:
        result = await self.session.execute(
            select(UsageEvent.created_at)
            .where(UsageEvent.user_id == user_id, UsageEvent.event_type.in_(("daily_active", "dashboard_loaded", "continuity_card_opened")))
            .order_by(UsageEvent.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _local_now(self, user: User) -> datetime:
        try:
            return datetime.now(ZoneInfo(user.timezone or "UTC"))
        except Exception:
            return datetime.now(timezone.utc)

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _out(row: Notification) -> dict:
        return {
            "id": row.id,
            "notificationType": row.notification_type,
            "channel": row.channel,
            "title": row.title,
            "message": row.message,
            "status": row.status,
            "priority": row.priority,
            "scheduledFor": row.scheduled_for,
            "sentAt": row.sent_at,
            "readAt": row.read_at,
            "metadata": row.metadata_ or {},
            "createdAt": row.created_at,
            "updatedAt": row.updated_at,
        }

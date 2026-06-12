from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import UsageEvent
from app.models.project import Project
from app.models.subscription import PaymentTransaction
from app.models.user import User


EVENTS = {
    "signups": ("signup_completed",),
    "logins": ("login_completed",),
    "projectsCreated": ("project_created",),
    "dailyBriefViews": ("daily_brief_viewed",),
    "openLoopViews": ("open_loops_viewed",),
    "upgradeClicks": ("upgrade_clicked",),
    "checkoutStarts": ("checkout_started",),
    "successfulPayments": ("payment_successful",),
}


class ProductAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self, *, window_days: int = 30) -> dict:
        today = date.today()
        start = today - timedelta(days=window_days - 1)
        previous_start = start - timedelta(days=window_days)
        previous_end = start - timedelta(days=1)

        current_counts = await self._window_counts(start, today)
        previous_counts = await self._window_counts(previous_start, previous_end)
        dau = await self._active_users(today, today)
        wau = await self._active_users(today - timedelta(days=6), today)

        metrics = [
            self._metric("signups", "Signups", current_counts["signups"], previous_counts["signups"]),
            self._metric("logins", "Logins", current_counts["logins"], previous_counts["logins"]),
            self._metric("projectsCreated", "Project Creation", current_counts["projectsCreated"], previous_counts["projectsCreated"]),
            self._metric("dailyActiveUsers", "Daily Active Users", dau, await self._active_users(today - timedelta(days=1), today - timedelta(days=1))),
            self._metric("weeklyActiveUsers", "Weekly Active Users", wau, await self._active_users(today - timedelta(days=13), today - timedelta(days=7))),
            self._metric("dailyBriefViews", "Daily Brief Views", current_counts["dailyBriefViews"], previous_counts["dailyBriefViews"]),
            self._metric("openLoopViews", "Open Loop Views", current_counts["openLoopViews"], previous_counts["openLoopViews"]),
            self._metric("upgradeClicks", "Upgrade Clicks", current_counts["upgradeClicks"], previous_counts["upgradeClicks"]),
            self._metric("checkoutStarts", "Checkout Starts", current_counts["checkoutStarts"], previous_counts["checkoutStarts"]),
            self._metric("successfulPayments", "Successful Payments", current_counts["successfulPayments"], previous_counts["successfulPayments"]),
        ]

        funnel_counts = [
            ("signups", "Signups", current_counts["signups"]),
            ("project_created", "Created Project", current_counts["projectsCreated"]),
            ("daily_brief_viewed", "Viewed Daily Brief", current_counts["dailyBriefViews"]),
            ("upgrade_clicked", "Clicked Upgrade", current_counts["upgradeClicks"]),
            ("checkout_started", "Started Checkout", current_counts["checkoutStarts"]),
            ("payment_successful", "Successful Payment", current_counts["successfulPayments"]),
        ]
        funnel = self._funnel(funnel_counts)
        return {
            "windowDays": window_days,
            "metrics": metrics,
            "funnel": funnel,
            "dropOffs": self._drop_offs(funnel),
            "daily": await self._daily_points(start, today),
        }

    async def _window_counts(self, start: date, end: date) -> dict[str, int]:
        counts = defaultdict(int)
        for key, event_types in EVENTS.items():
            result = await self.session.execute(
                select(func.count(UsageEvent.id)).where(
                    UsageEvent.event_type.in_(event_types),
                    func.date(UsageEvent.created_at) >= start.isoformat(),
                    func.date(UsageEvent.created_at) <= end.isoformat(),
                )
            )
            counts[key] = int(result.scalar() or 0)

        user_result = await self.session.execute(
            select(func.count(User.id)).where(
                func.date(User.created_at) >= start.isoformat(),
                func.date(User.created_at) <= end.isoformat(),
            )
        )
        counts["signups"] = max(counts["signups"], int(user_result.scalar() or 0))

        project_result = await self.session.execute(
            select(func.count(Project.id)).where(
                func.date(Project.created_at) >= start.isoformat(),
                func.date(Project.created_at) <= end.isoformat(),
            )
        )
        counts["projectsCreated"] = max(counts["projectsCreated"], int(project_result.scalar() or 0))

        payment_result = await self.session.execute(
            select(func.count(PaymentTransaction.id)).where(
                PaymentTransaction.status == "paid",
                func.date(PaymentTransaction.updated_at) >= start.isoformat(),
                func.date(PaymentTransaction.updated_at) <= end.isoformat(),
            )
        )
        counts["successfulPayments"] = max(counts["successfulPayments"], int(payment_result.scalar() or 0))
        return dict(counts)

    async def _active_users(self, start: date, end: date) -> int:
        result = await self.session.execute(
            select(func.count(distinct(UsageEvent.user_id))).where(
                UsageEvent.user_id.is_not(None),
                UsageEvent.event_type.in_(("daily_active", "dashboard_loaded", "page_view")),
                func.date(UsageEvent.created_at) >= start.isoformat(),
                func.date(UsageEvent.created_at) <= end.isoformat(),
            )
        )
        return int(result.scalar() or 0)

    async def _daily_points(self, start: date, end: date) -> list[dict]:
        points = {start + timedelta(days=i): {"date": (start + timedelta(days=i)).isoformat()} for i in range((end - start).days + 1)}
        for day, point in points.items():
            counts = await self._window_counts(day, day)
            point.update(counts)
            point["activeUsers"] = await self._active_users(day, day)
        return [points[key] for key in sorted(points)]

    @staticmethod
    def _metric(key: str, label: str, value: int, previous: int) -> dict:
        return {"key": key, "label": label, "value": value, "previous": previous, "change": value - previous}

    @staticmethod
    def _funnel(rows: list[tuple[str, str, int]]) -> list[dict]:
        out = []
        previous = None
        for key, label, count in rows:
            conversion = None if previous in (None, 0) else round(count / previous * 100, 1)
            out.append({"key": key, "label": label, "count": count, "conversionFromPrevious": conversion})
            previous = count
        return out

    @staticmethod
    def _drop_offs(funnel: list[dict]) -> list[dict]:
        drops = []
        for before, after in zip(funnel, funnel[1:]):
            lost = max(before["count"] - after["count"], 0)
            rate = round(lost / before["count"] * 100, 1) if before["count"] else 0
            drops.append({
                "label": f"{before['label']} to {after['label']}",
                "fromStep": before["label"],
                "toStep": after["label"],
                "lost": lost,
                "dropOffRate": rate,
            })
        return sorted(drops, key=lambda item: item["dropOffRate"], reverse=True)

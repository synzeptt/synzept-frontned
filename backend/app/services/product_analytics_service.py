from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import UsageEvent
from app.models.project import Project
from app.models.subscription import PaymentTransaction
from app.models.user import User
from app.api.v1.feedback import _feedback_since, _vote_counts, build_feedback_intelligence


EVENTS = {
    "signups": ("signup_completed",),
    "logins": ("login_completed",),
    "projectsCreated": ("project_created",),
    "firstChat": ("onboarding_first_ai_success", "chat_message_sent", "message_sent"),
    "firstMemory": ("onboarding_memory_initialized", "memory_created"),
    "firstReturnVisit": ("first_return_visit",),
    "onboardingCompleted": ("onboarding_completed", "first_run_intelligence_completed"),
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
        onboarding = {
            "signupCompleted": current_counts["signups"],
            "firstChat": await self._distinct_event_users(start, today, *EVENTS["firstChat"]),
            "firstMemory": await self._distinct_event_users(start, today, *EVENTS["firstMemory"]),
            "firstReturnVisit": await self._distinct_event_users(start, today, *EVENTS["firstReturnVisit"]),
            "onboardingCompleted": await self._distinct_event_users(start, today, *EVENTS["onboardingCompleted"]),
        }
        previous_onboarding_completed = await self._distinct_event_users(previous_start, previous_end, *EVENTS["onboardingCompleted"])
        dau = await self._active_users(today, today)
        wau = await self._active_users(today - timedelta(days=6), today)
        total_users = await self._total_users()
        active_users = await self._active_users(start, today)
        first_mission = await self._distinct_event_users(start, today, "first_run_intelligence_completed", "onboarding_2_confirmed")
        returned_next_day = await self._returned_after_days(start, today, 1)

        metrics = [
            self._metric("signups", "Signups", current_counts["signups"], previous_counts["signups"]),
            self._metric("onboardingCompleted", "Onboarding Completed", onboarding["onboardingCompleted"], previous_onboarding_completed),
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
            ("first_chat", "First Chat", onboarding["firstChat"]),
            ("first_memory", "First Memory", onboarding["firstMemory"]),
            ("first_return_visit", "First Return Visit", onboarding["firstReturnVisit"]),
            ("onboarding_completed", "Onboarding Completed", onboarding["onboardingCompleted"]),
            ("project_created", "Created Project", current_counts["projectsCreated"]),
            ("daily_brief_viewed", "Viewed Daily Brief", current_counts["dailyBriefViews"]),
            ("upgrade_clicked", "Clicked Upgrade", current_counts["upgradeClicks"]),
            ("checkout_started", "Started Checkout", current_counts["checkoutStarts"]),
            ("payment_successful", "Successful Payment", current_counts["successfulPayments"]),
        ]
        funnel = self._funnel(funnel_counts)
        retention = await self._retention(start, today)
        most_used = await self._feature_usage(start, today, most_used=True)
        least_used = await self._feature_usage(start, today, most_used=False)
        feedback = build_feedback_intelligence(await _feedback_since(self.session, start), await _vote_counts(self.session))
        activation = {
            "completedOnboarding": onboarding["onboardingCompleted"],
            "createdFirstMission": first_mission,
            "returnedNextDay": returned_next_day,
            "completedOnboardingRate": self._rate(onboarding["onboardingCompleted"], current_counts["signups"]),
            "createdFirstMissionRate": self._rate(first_mission, current_counts["signups"]),
            "returnedNextDayRate": self._rate(returned_next_day, current_counts["signups"]),
        }
        return {
            "windowDays": window_days,
            "users": {
                "totalUsers": total_users,
                "newUsers": current_counts["signups"],
                "activeUsers": active_users,
            },
            "activation": activation,
            "metrics": metrics,
            "funnel": funnel,
            "dropOffs": self._drop_offs(funnel),
            "daily": await self._daily_points(start, today),
            "feedback": feedback,
            "mostUsedFeatures": most_used,
            "leastUsedFeatures": least_used,
            "confusingAreas": self._confusing_areas(feedback),
            "founderAlerts": self._founder_alerts(
                signups=current_counts["signups"],
                active_users=active_users,
                activation=activation,
                retention=retention,
                most_used=most_used,
                least_used=least_used,
                feedback=feedback,
            ),
            "retention": retention,
            "onboarding": onboarding,
        }

    async def _total_users(self) -> int:
        result = await self.session.execute(select(func.count(User.id)).where(User.deleted_at.is_(None)))
        return int(result.scalar() or 0)

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

    async def _distinct_event_users(self, start: date, end: date, *event_types: str) -> int:
        result = await self.session.execute(
            select(func.count(distinct(UsageEvent.user_id))).where(
                UsageEvent.user_id.is_not(None),
                UsageEvent.event_type.in_(event_types),
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

    async def _feature_usage(self, start: date, end: date, *, most_used: bool) -> list[dict]:
        result = await self.session.execute(
            select(
                UsageEvent.surface,
                func.count(UsageEvent.id),
                func.count(distinct(UsageEvent.user_id)),
                func.coalesce(func.sum(UsageEvent.value), 0),
            )
            .where(
                UsageEvent.surface.is_not(None),
                UsageEvent.event_type.in_(("page_view", "time_spent", "chat_message_sent", "message_sent", "feedback_submitted")),
                func.date(UsageEvent.created_at) >= start.isoformat(),
                func.date(UsageEvent.created_at) <= end.isoformat(),
            )
            .group_by(UsageEvent.surface)
        )
        rows = [
            {
                "feature": str(surface or "unknown"),
                "events": int(events or 0),
                "users": int(users or 0),
                "timeSpentSeconds": int(seconds or 0),
            }
            for surface, events, users, seconds in result.all()
        ]
        return sorted(rows, key=lambda item: (item["users"], item["events"], item["timeSpentSeconds"]), reverse=most_used)[:12]

    async def _retention(self, start: date, end: date) -> dict:
        signup_users = await self.session.execute(
            select(User.id).where(
                func.date(User.created_at) >= start.isoformat(),
                func.date(User.created_at) <= end.isoformat(),
            )
        )
        cohort = {user_id for user_id in signup_users.scalars()}
        if not cohort:
            return {"signupCohort": 0, "returnedUsers": 0, "retentionRate": 0, "day1": 0, "day7": 0, "day30": 0}
        returned = await self.session.execute(
            select(distinct(UsageEvent.user_id)).where(
                UsageEvent.user_id.in_(cohort),
                UsageEvent.event_type.in_(("first_return_visit", "return_session", "daily_active")),
                func.date(UsageEvent.created_at) >= start.isoformat(),
                func.date(UsageEvent.created_at) <= end.isoformat(),
            )
        )
        returned_users = {user_id for user_id in returned.scalars() if user_id}
        return {
            "signupCohort": len(cohort),
            "returnedUsers": len(returned_users),
            "retentionRate": round(len(returned_users) / len(cohort) * 100, 1),
            "day1": await self._retention_after_days(cohort, 1),
            "day7": await self._retention_after_days(cohort, 7),
            "day30": await self._retention_after_days(cohort, 30),
        }

    async def _returned_after_days(self, start: date, end: date, days_after_signup: int) -> int:
        signup_rows = await self.session.execute(
            select(User.id, func.date(User.created_at)).where(
                func.date(User.created_at) >= start.isoformat(),
                func.date(User.created_at) <= end.isoformat(),
            )
        )
        users_by_target: dict[str, set] = defaultdict(set)
        for user_id, signup_day in signup_rows.all():
            target = date.fromisoformat(str(signup_day)) + timedelta(days=days_after_signup)
            if target <= end:
                users_by_target[target.isoformat()].add(user_id)
        returned: set = set()
        for target, users in users_by_target.items():
            result = await self.session.execute(
                select(distinct(UsageEvent.user_id)).where(
                    UsageEvent.user_id.in_(users),
                    UsageEvent.event_type.in_(("daily_active", "dashboard_loaded", "page_view", "return_session", "first_return_visit")),
                    func.date(UsageEvent.created_at) == target,
                )
            )
            returned.update(user_id for user_id in result.scalars() if user_id)
        return len(returned)

    async def _retention_after_days(self, cohort: set, days_after_signup: int) -> float:
        if not cohort:
            return 0
        signup_rows = await self.session.execute(select(User.id, func.date(User.created_at)).where(User.id.in_(cohort)))
        eligible = 0
        returned: set = set()
        today = date.today()
        for user_id, signup_day in signup_rows.all():
            target = date.fromisoformat(str(signup_day)) + timedelta(days=days_after_signup)
            if target > today:
                continue
            eligible += 1
            result = await self.session.execute(
                select(UsageEvent.user_id).where(
                    UsageEvent.user_id == user_id,
                    UsageEvent.event_type.in_(("daily_active", "dashboard_loaded", "page_view", "return_session", "first_return_visit")),
                    func.date(UsageEvent.created_at) == target.isoformat(),
                ).limit(1)
            )
            if result.scalar_one_or_none():
                returned.add(user_id)
        return self._rate(len(returned), eligible)

    @staticmethod
    def _confusing_areas(feedback: dict) -> list[dict]:
        rows = [
            *feedback.get("most_common_frustrations", []),
            *feedback.get("top_reported_issues", []),
        ]
        confusing = [
            row for row in rows
            if any(word in f"{row.get('title', '')} {row.get('detail', '')}".casefold() for word in ("confusing", "unclear", "hard", "lost", "where", "understand"))
        ]
        return confusing[:8] or rows[:8]

    def _founder_alerts(
        self,
        *,
        signups: int,
        active_users: int,
        activation: dict,
        retention: dict,
        most_used: list[dict],
        least_used: list[dict],
        feedback: dict,
    ) -> list[dict]:
        alerts: list[dict] = []
        incomplete_rate = round(100 - activation["completedOnboardingRate"], 1) if signups else 0
        if signups and incomplete_rate >= 50:
            alerts.append({
                "title": f"{incomplete_rate}% of users never finish onboarding",
                "detail": f"{activation['completedOnboarding']} of {signups} new users completed onboarding in this window.",
                "severity": "high" if incomplete_rate >= 80 else "medium",
                "metric": "activation",
            })
        daily_brief = next((item for item in most_used if item["feature"] == "daily_brief"), None)
        if active_users and daily_brief:
            rate = self._rate(daily_brief["users"], active_users)
            alerts.append({
                "title": f"Daily Brief is used by {rate}% of active users",
                "detail": f"{daily_brief['users']} active users opened Daily Brief.",
                "severity": "low" if rate >= 50 else "medium",
                "metric": "daily_brief",
            })
        open_loops = next((item for item in [*most_used, *least_used] if item["feature"] in {"open_loops", "open-loops"}), None)
        if active_users and (not open_loops or self._rate(open_loops["users"], active_users) < 20):
            alerts.append({
                "title": "Open Loops page has low engagement",
                "detail": "Users may not be discovering unfinished work as a daily habit.",
                "severity": "medium",
                "metric": "open_loops",
            })
        if retention.get("day7", 0) < 20 and signups:
            alerts.append({
                "title": f"Day 7 retention is {retention.get('day7', 0)}%",
                "detail": "The product is not yet creating a strong weekly return loop.",
                "severity": "high",
                "metric": "retention",
            })
        for item in feedback.get("most_common_frustrations", [])[:2]:
            alerts.append({
                "title": item.get("title", "User confusion detected"),
                "detail": item.get("detail", "Feedback suggests this area needs attention."),
                "severity": "medium",
                "metric": "feedback",
            })
        return alerts[:8]

    @staticmethod
    def _rate(value: int, total: int) -> float:
        return round(value / total * 100, 1) if total else 0

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

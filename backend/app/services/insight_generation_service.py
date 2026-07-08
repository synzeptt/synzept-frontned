from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_understanding import UserUnderstanding
from app.schemas.user_understanding import UnderstandingInsightOut
from app.services.priority_engine import PriorityEngine


class InsightGenerationService:
    """Generates compact, explainable insights from the maintained understanding model."""

    def __init__(self, session: AsyncSession, *, priorities: PriorityEngine | None = None) -> None:
        self.session = session
        self.priorities = priorities or PriorityEngine(session)

    async def insights_for_user(self, user_id: UUID) -> list[UnderstandingInsightOut]:
        items = await self._items(user_id)
        by_category = self._group(items)
        priority_rows = await self.priorities.priorities_for_user(user_id, limit=3)
        insights: list[UnderstandingInsightOut] = []

        if by_category.get("missions") and by_category.get("current_focus"):
            insights.append(
                UnderstandingInsightOut(
                    type="alignment",
                    title="Mission and current focus are both visible.",
                    description=f"Mission: {by_category['missions'][0]}. Current focus: {by_category['current_focus'][0]}.",
                    confidence=0.82,
                    evidence=[by_category["missions"][0], by_category["current_focus"][0]],
                    action=priority_rows[0]["action"] if priority_rows else None,
                )
            )
        if by_category.get("open_loops"):
            insights.append(
                UnderstandingInsightOut(
                    type="open_loop",
                    title="Open loops are competing for attention.",
                    description=f"{len(by_category['open_loops'])} open loop signal(s) are active. Start with the most recent or highest priority one.",
                    confidence=0.78,
                    evidence=by_category["open_loops"][:3],
                    action=priority_rows[0]["action"] if priority_rows else "Close or clarify one open loop.",
                )
            )
        if by_category.get("current_struggles"):
            insights.append(
                UnderstandingInsightOut(
                    type="struggle",
                    title="A current struggle may be blocking progress.",
                    description=by_category["current_struggles"][0],
                    confidence=0.74,
                    evidence=by_category["current_struggles"][:2],
                    action="Turn the struggle into one concrete next action.",
                )
            )
        if by_category.get("preferences"):
            insights.append(
                UnderstandingInsightOut(
                    type="preference",
                    title="Personal preferences should shape how Synzept helps.",
                    description=by_category["preferences"][0],
                    confidence=0.7,
                    evidence=by_category["preferences"][:2],
                )
            )
        if priority_rows:
            insights.append(
                UnderstandingInsightOut(
                    type="priority",
                    title="Recommended next action is ready.",
                    description=priority_rows[0]["reason"],
                    confidence=min(priority_rows[0]["score"], 0.95),
                    evidence=[priority_rows[0]["title"]],
                    action=priority_rows[0]["action"],
                )
            )
        if not insights:
            insights.append(
                UnderstandingInsightOut(
                    type="empty_state",
                    title="Synzept needs more signal.",
                    description="Add a mission, current focus, or a few meaningful conversations to build the understanding profile.",
                    confidence=0.6,
                    action="Add your mission in Synzept Knows You.",
                )
            )
        return insights[:6]

    async def _items(self, user_id: UUID) -> list[UserUnderstanding]:
        result = await self.session.execute(
            select(UserUnderstanding)
            .where(UserUnderstanding.user_id == user_id, UserUnderstanding.category != "profile")
            .order_by(UserUnderstanding.updated_at.desc())
        )
        return list(result.scalars())

    @staticmethod
    def _group(items: list[UserUnderstanding]) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for item in items:
            if not item.value.strip():
                continue
            grouped.setdefault(item.category, [])
            if item.value not in grouped[item.category]:
                grouped[item.category].append(item.value)
        return grouped

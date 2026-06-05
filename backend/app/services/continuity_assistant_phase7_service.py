from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.continuity_assistant_phase7 import ContinuityAssistantSnapshot
from app.services.context_engine_phase6_service import ContextEnginePhase6Service


class ContinuityAssistantPhase7Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def current(self, user_id: UUID) -> dict:
        result = await self.session.execute(
            select(ContinuityAssistantSnapshot)
            .where(ContinuityAssistantSnapshot.user_id == user_id)
            .order_by(ContinuityAssistantSnapshot.created_at.desc())
        )
        snapshot = result.scalars().first()
        if snapshot:
            return self._snapshot_out(snapshot)
        return await self.refresh(user_id)

    async def refresh(self, user_id: UUID) -> dict:
        context = await ContextEnginePhase6Service(self.session).refresh(user_id)
        themes = context["activeThemes"]
        what_changed = [item for item in themes if str(item.get("type", "")).startswith("timeline_")][:5]
        recent_progress = [item for item in what_changed if item.get("type") in {"timeline_progress", "timeline_achievement", "timeline_milestone"}]
        if not what_changed and themes:
            what_changed = themes[:3]
        what_matters = [
            {
                "title": context["currentFocus"].get("title", "Current focus"),
                "detail": context["currentFocus"].get("detail", ""),
                "type": "current_focus",
            },
            *context["importantContext"][:4],
        ]
        snapshot = ContinuityAssistantSnapshot(
            user_id=user_id,
            context_snapshot_id=context["id"],
            what_changed=what_changed,
            what_matters=what_matters[:5],
            open_loops=context["openLoops"][:6],
            recent_progress=recent_progress[:5],
            recommended_next_step=context["recommendedNextStep"],
        )
        self.session.add(snapshot)
        await self.session.flush()
        return self._snapshot_out(snapshot)

    @staticmethod
    def _snapshot_out(snapshot: ContinuityAssistantSnapshot) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "id": snapshot.id,
            "userId": snapshot.user_id,
            "contextSnapshotId": snapshot.context_snapshot_id,
            "whatChanged": snapshot.what_changed or [],
            "whatMatters": snapshot.what_matters or [],
            "openLoops": snapshot.open_loops or [],
            "recentProgress": snapshot.recent_progress or [],
            "recommendedNextStep": snapshot.recommended_next_step or {},
            "createdAt": snapshot.created_at or now,
            "updatedAt": snapshot.updated_at or snapshot.created_at or now,
        }

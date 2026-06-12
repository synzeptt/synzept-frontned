from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import UsageEvent


class UsageEventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def track(
        self,
        *,
        user_id: UUID | None,
        event_type: str,
        surface: str | None = None,
        metadata: dict | None = None,
        value: int | None = None,
    ) -> None:
        if user_id is None:
            return
        self.session.add(
            UsageEvent(
                user_id=user_id,
                event_type=event_type,
                surface=surface,
                value=value,
                metadata_=metadata or {},
            )
        )
        await self.session.flush()

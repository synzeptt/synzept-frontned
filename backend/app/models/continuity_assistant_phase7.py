import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import JSONB, UUID


class ContinuityAssistantSnapshot(Base):
    __tablename__ = "continuity_assistant_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    context_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("context_snapshots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    what_changed: Mapped[list] = mapped_column(JSONB, default=list)
    what_matters: Mapped[list] = mapped_column(JSONB, default=list)
    open_loops: Mapped[list] = mapped_column(JSONB, default=list)
    recent_progress: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_next_step: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

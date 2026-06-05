import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import JSONB, UUID


class DailyBriefSnapshot(Base):
    __tablename__ = "daily_brief_snapshots"
    __table_args__ = (UniqueConstraint("user_id", "brief_date", name="uq_daily_brief_snapshots_user_date"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    context_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("context_snapshots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    brief_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    what_matters_today: Mapped[list] = mapped_column(JSONB, default=list)
    open_loops: Mapped[list] = mapped_column(JSONB, default=list)
    recommended_next_step: Mapped[dict] = mapped_column(JSONB, default=dict)
    recent_progress: Mapped[list] = mapped_column(JSONB, default=list)
    context_to_remember: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

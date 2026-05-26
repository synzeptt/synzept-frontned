"""Daily activity summaries for briefings and continuity."""

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from app.database.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin


class DailySummary(Base, TimestampMixin):
    __tablename__ = "daily_summaries"
    __table_args__ = (
        UniqueConstraint("user_id", "summary_date", "summary_kind", name="uq_daily_summaries_user_date_kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    summary_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    summary_kind: Mapped[str] = mapped_column(String(20), default="morning", index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    completed_work: Mapped[list] = mapped_column(JSONB, default=list)
    unfinished_priorities: Mapped[list] = mapped_column(JSONB, default=list)
    insights: Mapped[list] = mapped_column(JSONB, default=list)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    user = relationship("User", back_populates="daily_summaries")

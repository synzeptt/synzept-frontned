import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin
from app.database.types import UUID


class TimelineEvent(Base, TimestampMixin):
    __tablename__ = "timeline_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('milestone', 'decision', 'learning', 'achievement', 'progress')",
            name="ck_timeline_events_type",
        ),
        CheckConstraint("importance >= 0 AND importance <= 1", name="ck_timeline_events_importance"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    importance: Mapped[float] = mapped_column(Float, default=0.5, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    user = relationship("User", back_populates="timeline_events")
    project = relationship("Project")

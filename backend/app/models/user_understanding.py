import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text
from app.database.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin


class UserUnderstanding(Base, TimestampMixin):
    __tablename__ = "user_understanding"
    __table_args__ = (
        CheckConstraint("source IN ('user', 'learned')", name="ck_user_understanding_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="user", index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    learned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    personal: Mapped[dict] = mapped_column(JSONB, default=dict)
    professional: Mapped[dict] = mapped_column(JSONB, default=dict)
    goals: Mapped[dict] = mapped_column(JSONB, default=dict)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    learning: Mapped[dict] = mapped_column(JSONB, default=dict)
    current_focus: Mapped[dict] = mapped_column(JSONB, default=dict)

    user = relationship("User", back_populates="understanding")

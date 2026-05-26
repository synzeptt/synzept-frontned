"""User intelligence profile — goals, preferences, and work style."""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from app.database.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    communication_style: Mapped[str] = mapped_column(String(40), default="balanced")
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    profile_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    goals: Mapped[list] = mapped_column(JSONB, default=list)
    work_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    communication_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    routines: Mapped[dict] = mapped_column(JSONB, default=dict)
    personality_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)
    productivity_style: Mapped[str | None] = mapped_column(String(80), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="profile")

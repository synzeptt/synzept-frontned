import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import TimestampMixin
from app.database.types import JSONB, UUID


class PreparedDeliverable(Base, TimestampMixin):
    __tablename__ = "prepared_deliverables"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    deliverable_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="preparing", index=True)
    created_from: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_events: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_apps: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    estimated_time_saved_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    approval_required: Mapped[bool] = mapped_column(default=False, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    content_json: Mapped[dict[str, Any]] = mapped_column("content_json", JSONB, nullable=False, default=dict)
    execution_actions: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, Integer, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin
from app.database.types import JSONB, UUID


class ExecutionState(Base, TimestampMixin):
    """Persists execution state for resumable workflows."""

    __tablename__ = "execution_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    execution_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    workflow_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", index=True)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0)
    current_step_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    browser_session_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    execution_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    execution_session: Mapped[dict] = mapped_column(JSONB, default=dict)
    workflow_steps: Mapped[list] = mapped_column(JSONB, default=list)
    clarification_answers: Mapped[dict] = mapped_column(JSONB, default=dict)
    progress_log: Mapped[list] = mapped_column(JSONB, default=list)
    artifacts: Mapped[list] = mapped_column(JSONB, default=list)
    error_log: Mapped[list] = mapped_column(JSONB, default=list)
    approval_pending: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_data: Mapped[dict] = mapped_column(JSONB, default=dict)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExecutionMetrics(Base, TimestampMixin):
    """Records metrics for every execution for observability and reliability tracking."""

    __tablename__ = "execution_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    execution_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    workflow_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    browser_recoveries: Mapped[int] = mapped_column(Integer, default=0)
    connector_failures: Mapped[int] = mapped_column(Integer, default=0)
    approval_requests: Mapped[int] = mapped_column(Integer, default=0)
    user_interventions: Mapped[int] = mapped_column(Integer, default=0)
    artifacts_generated: Mapped[int] = mapped_column(Integer, default=0)
    steps_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)


class ExecutionTimeline(Base, TimestampMixin):
    """Records execution progress timeline for live updates."""

    __tablename__ = "execution_timelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    execution_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(60), nullable=False)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="running")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

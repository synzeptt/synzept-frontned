import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from app.database.types import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin, TimestampMixin


class Memory(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    memory_type: Mapped[str] = mapped_column(String(50), default="work", index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance_score: Mapped[float] = mapped_column(Float, default=0.5, index=True)
    recency_score: Mapped[float] = mapped_column(Float, default=1.0)
    retrieval_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    # Compatibility fields for the earlier memory prototype. New code should use
    # memory_type, importance_score, and retrieval_count.
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("embeddings.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", back_populates="memories")
    project = relationship("Project", back_populates="memories")

    @property
    def importance(self) -> float:
        return self.importance_score

    @importance.setter
    def importance(self, value: float) -> None:
        self.importance_score = value

    @property
    def access_count(self) -> int:
        return self.retrieval_count

    @access_count.setter
    def access_count(self, value: int) -> None:
        self.retrieval_count = value

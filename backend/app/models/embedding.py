import uuid

from sqlalchemy import ForeignKey, String, Text
from app.database.types import JSONB, UUID, Vector
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import get_settings
from app.database.base import Base
from app.database.mixins import TimestampMixin

settings = get_settings()


class Embedding(Base, TimestampMixin):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.embedding_dimensions))
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False, default="openai", index=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

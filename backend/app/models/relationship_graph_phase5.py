import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.types import UUID


class RelationshipNode(Base):
    __tablename__ = "relationship_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_type IN ('user', 'goal', 'project', 'task', 'open_loop', 'decision', 'timeline_event', 'note', 'memory', 'conversation')",
            name="ck_relationship_nodes_type",
        ),
        UniqueConstraint("user_id", "node_type", "entity_id", name="uq_relationship_nodes_entity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    outgoing_edges = relationship(
        "RelationshipEdge",
        foreign_keys="RelationshipEdge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan",
    )
    incoming_edges = relationship(
        "RelationshipEdge",
        foreign_keys="RelationshipEdge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan",
    )


class RelationshipEdge(Base):
    __tablename__ = "relationship_edges"
    __table_args__ = (
        CheckConstraint("strength >= 0 AND strength <= 1", name="ck_relationship_edges_strength"),
        UniqueConstraint(
            "user_id",
            "source_node_id",
            "target_node_id",
            "relationship_type",
            name="uq_relationship_edges_relation",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("relationship_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("relationship_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    source_node = relationship("RelationshipNode", foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node = relationship("RelationshipNode", foreign_keys=[target_node_id], back_populates="incoming_edges")

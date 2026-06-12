import uuid

from sqlalchemy import CheckConstraint, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin
from app.database.types import UUID


class GraphNode(Base, TimestampMixin):
    __tablename__ = "graph_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    node_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    user = relationship("User", back_populates="graph_nodes")
    outgoing_edges = relationship("GraphEdge", foreign_keys="GraphEdge.source_node_id", cascade="all, delete-orphan")
    incoming_edges = relationship("GraphEdge", foreign_keys="GraphEdge.target_node_id", cascade="all, delete-orphan")


class GraphEdge(Base, TimestampMixin):
    __tablename__ = "graph_edges"
    __table_args__ = (
        CheckConstraint("strength >= 0 AND strength <= 1", name="ck_graph_edges_strength"),
        UniqueConstraint("user_id", "source_node_id", "target_node_id", "relationship_type", name="uq_graph_edges_relation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), index=True)
    target_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("graph_nodes.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    strength: Mapped[float] = mapped_column(Float, default=0.5)

    user = relationship("User", back_populates="graph_edges")

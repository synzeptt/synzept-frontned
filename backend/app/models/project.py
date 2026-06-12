import uuid

from sqlalchemy import ForeignKey, String, Text
from app.database.types import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import SoftDeleteMixin, TimestampMixin


class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_focus: Mapped[str] = mapped_column(Text, default="")
    recommended_next_step: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    context_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="projects")
    conversations = relationship("Conversation", back_populates="project")
    notes = relationship("Note", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    goals = relationship("Goal", back_populates="project")
    memories = relationship("Memory", back_populates="project")
    context_entries = relationship("ProjectContext", back_populates="project", cascade="all, delete-orphan")
    intelligence = relationship("ProjectIntelligence", back_populates="project", uselist=False, cascade="all, delete-orphan")
    decisions = relationship("ProjectDecision", back_populates="project", cascade="all, delete-orphan")
    open_loops = relationship("ProjectOpenLoop", back_populates="project", cascade="all, delete-orphan")

    def __init__(self, **kwargs):
        if "name" in kwargs and "title" not in kwargs:
            kwargs["title"] = kwargs["name"]
        elif "title" in kwargs and "name" not in kwargs:
            kwargs["name"] = kwargs["title"]
        super().__init__(**kwargs)

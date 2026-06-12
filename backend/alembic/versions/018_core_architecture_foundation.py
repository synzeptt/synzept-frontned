"""Shared V2 core architecture entities.

Revision ID: 018
Revises: 017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("title", sa.String(length=200), nullable=True))
    op.execute("UPDATE projects SET title = name WHERE title IS NULL")
    op.add_column("goals", sa.Column("target_date", sa.Date(), nullable=True))
    op.create_index("ix_goals_target_date", "goals", ["target_date"])
    op.add_column("memories", sa.Column("confidence", sa.Float(), nullable=False, server_default="1"))
    op.add_column("memories", sa.Column("source", sa.String(length=80), nullable=False, server_default="system"))
    op.create_index("ix_memories_source", "memories", ["source"])

    op.create_table(
        "timeline_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "event_type", "importance", "event_date"):
        op.create_index(f"ix_timeline_events_{column}", "timeline_events", [column])

    op.create_table(
        "learning_signals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("signal_type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'ignored')", name="ck_learning_signals_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "signal_type", "status"):
        op.create_index(f"ix_learning_signals_{column}", "learning_signals", [column])

    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("node_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graph_nodes_user_id", "graph_nodes", ["user_id"])
    op.create_index("ix_graph_nodes_node_type", "graph_nodes", ["node_type"])

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_node_id", sa.UUID(), nullable=False),
        sa.Column("target_node_id", sa.UUID(), nullable=False),
        sa.Column("relationship_type", sa.String(length=100), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("strength >= 0 AND strength <= 1", name="ck_graph_edges_strength"),
        sa.ForeignKeyConstraint(["source_node_id"], ["graph_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["graph_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_node_id", "target_node_id", "relationship_type", name="uq_graph_edges_relation"),
    )
    for column in ("user_id", "source_node_id", "target_node_id", "relationship_type"):
        op.create_index(f"ix_graph_edges_{column}", "graph_edges", [column])


def downgrade() -> None:
    op.drop_table("graph_edges")
    op.drop_table("graph_nodes")
    op.drop_table("learning_signals")
    op.drop_table("timeline_events")
    op.drop_index("ix_memories_source", table_name="memories")
    op.drop_column("memories", "source")
    op.drop_column("memories", "confidence")
    op.drop_index("ix_goals_target_date", table_name="goals")
    op.drop_column("goals", "target_date")
    op.drop_column("projects", "title")

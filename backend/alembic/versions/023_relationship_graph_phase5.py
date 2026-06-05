"""relationship graph phase 5

Revision ID: 023
Revises: 022
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import UUID


revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "relationship_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "node_type IN ('user', 'goal', 'project', 'memory', 'decision', 'timeline_event')",
            name="ck_relationship_nodes_type",
        ),
        sa.UniqueConstraint("user_id", "node_type", "entity_id", name="uq_relationship_nodes_entity"),
    )
    op.create_index("ix_relationship_nodes_user_id", "relationship_nodes", ["user_id"])
    op.create_index("ix_relationship_nodes_node_type", "relationship_nodes", ["node_type"])
    op.create_index("ix_relationship_nodes_entity_id", "relationship_nodes", ["entity_id"])

    op.create_table(
        "relationship_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_node_id", UUID(as_uuid=True), sa.ForeignKey("relationship_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_node_id", UUID(as_uuid=True), sa.ForeignKey("relationship_nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("strength", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("strength >= 0 AND strength <= 1", name="ck_relationship_edges_strength"),
        sa.UniqueConstraint(
            "user_id",
            "source_node_id",
            "target_node_id",
            "relationship_type",
            name="uq_relationship_edges_relation",
        ),
    )
    op.create_index("ix_relationship_edges_user_id", "relationship_edges", ["user_id"])
    op.create_index("ix_relationship_edges_source_node_id", "relationship_edges", ["source_node_id"])
    op.create_index("ix_relationship_edges_target_node_id", "relationship_edges", ["target_node_id"])
    op.create_index("ix_relationship_edges_relationship_type", "relationship_edges", ["relationship_type"])


def downgrade() -> None:
    op.drop_index("ix_relationship_edges_relationship_type", table_name="relationship_edges")
    op.drop_index("ix_relationship_edges_target_node_id", table_name="relationship_edges")
    op.drop_index("ix_relationship_edges_source_node_id", table_name="relationship_edges")
    op.drop_index("ix_relationship_edges_user_id", table_name="relationship_edges")
    op.drop_table("relationship_edges")
    op.drop_index("ix_relationship_nodes_entity_id", table_name="relationship_nodes")
    op.drop_index("ix_relationship_nodes_node_type", table_name="relationship_nodes")
    op.drop_index("ix_relationship_nodes_user_id", table_name="relationship_nodes")
    op.drop_table("relationship_nodes")

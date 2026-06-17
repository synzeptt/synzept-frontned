"""relationship context graph entity expansion

Revision ID: 032_relationship_context_graph
Revises: 031_personal_intelligence_v1
Create Date: 2026-06-17
"""

from typing import Sequence, Union

from alembic import op


revision: str = "032_relationship_context_graph"
down_revision: Union[str, tuple[str, str]] = "031_personal_intelligence_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL cannot alter a named CHECK constraint in place. SQLite local
    # compatibility is handled by initialize_local_database.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("ck_relationship_nodes_type", "relationship_nodes", type_="check")
        op.create_check_constraint(
            "ck_relationship_nodes_type",
            "relationship_nodes",
            "node_type IN ('user', 'goal', 'project', 'task', 'open_loop', 'decision', 'timeline_event', 'note', 'memory', 'knowledge', 'person', 'conversation')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("ck_relationship_nodes_type", "relationship_nodes", type_="check")
        op.create_check_constraint(
            "ck_relationship_nodes_type",
            "relationship_nodes",
            "node_type IN ('user', 'goal', 'project', 'task', 'open_loop', 'decision', 'timeline_event', 'note', 'memory', 'conversation')",
        )

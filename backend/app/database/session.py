from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine_options = {
    "echo": settings.environment == "development",
    "pool_pre_ping": True,
}
if settings.is_sqlite:
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options["pool_size"] = settings.database_pool_size
    engine_options["max_overflow"] = settings.database_max_overflow

engine = create_async_engine(settings.database_url, **engine_options)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def initialize_local_database() -> None:
    if not settings.is_sqlite:
        return
    from app.database.base import Base
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_local_memory_schema)
        await conn.run_sync(_ensure_local_goal_schema)
        await conn.run_sync(_ensure_local_workspace_schema)
        await conn.run_sync(_ensure_local_core_schema)
        await conn.run_sync(_ensure_local_knows_you_schema)
        await conn.run_sync(_ensure_local_project_intelligence_phase2_schema)
        await conn.run_sync(_ensure_local_timeline_phase3_schema)
        await conn.run_sync(_ensure_local_learning_engine_phase4_schema)
        await conn.run_sync(_ensure_local_open_loop_engine_schema)
        await conn.run_sync(_ensure_local_relationship_graph_schema)
        await conn.run_sync(_ensure_local_subscription_schema)
        await conn.run_sync(_ensure_local_notification_schema)


def _ensure_local_memory_schema(connection) -> None:
    """Apply additive SQLite compatibility changes for existing founder databases."""
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(memories)")}
    if columns and "version" not in columns:
        connection.exec_driver_sql("ALTER TABLE memories ADD COLUMN version INTEGER NOT NULL DEFAULT 1")


def _ensure_local_goal_schema(connection) -> None:
    """Link legacy SQLite task tables to milestones without resetting local data."""
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(tasks)")}
    if columns and "milestone_id" not in columns:
        connection.exec_driver_sql("ALTER TABLE tasks ADD COLUMN milestone_id CHAR(36)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_tasks_milestone_id ON tasks (milestone_id)")


def _ensure_local_workspace_schema(connection) -> None:
    """Add workspace note links to existing SQLite founder databases."""
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(notes)")}
    if columns and "goal_id" not in columns:
        connection.exec_driver_sql("ALTER TABLE notes ADD COLUMN goal_id CHAR(36)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notes_goal_id ON notes (goal_id)")
    if columns and "tags" not in columns:
        connection.exec_driver_sql("ALTER TABLE notes ADD COLUMN tags JSON NOT NULL DEFAULT '[]'")


def _ensure_local_core_schema(connection) -> None:
    """Add canonical V2 fields to existing SQLite databases without data loss."""
    project_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(projects)")}
    if project_columns and "title" not in project_columns:
        connection.exec_driver_sql("ALTER TABLE projects ADD COLUMN title VARCHAR(200)")
        connection.exec_driver_sql("UPDATE projects SET title = name WHERE title IS NULL")

    goal_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(goals)")}
    if goal_columns and "target_date" not in goal_columns:
        connection.exec_driver_sql("ALTER TABLE goals ADD COLUMN target_date DATE")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_goals_target_date ON goals (target_date)")

    memory_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(memories)")}
    if memory_columns and "confidence" not in memory_columns:
        connection.exec_driver_sql("ALTER TABLE memories ADD COLUMN confidence FLOAT NOT NULL DEFAULT 1")
    if memory_columns and "source" not in memory_columns:
        connection.exec_driver_sql("ALTER TABLE memories ADD COLUMN source VARCHAR(80) NOT NULL DEFAULT 'system'")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_memories_source ON memories (source)")


def _ensure_local_knows_you_schema(connection) -> None:
    """Add Phase 1 Synzept Knows You columns to existing SQLite databases."""
    understanding_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(user_understanding)")}
    for column in ("personal", "professional", "goals", "preferences", "learning", "current_focus"):
        if understanding_columns and column not in understanding_columns:
            connection.exec_driver_sql(f"ALTER TABLE user_understanding ADD COLUMN {column} JSON NOT NULL DEFAULT '{{}}'")

    suggestion_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(learning_suggestions)")}
    if suggestion_columns and "updated_at" not in suggestion_columns:
        connection.exec_driver_sql("ALTER TABLE learning_suggestions ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")


def _ensure_local_project_intelligence_phase2_schema(connection) -> None:
    """Add Phase 2 Project Intelligence columns to existing SQLite databases."""
    project_columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(projects)")}
    if project_columns and "current_focus" not in project_columns:
        connection.exec_driver_sql("ALTER TABLE projects ADD COLUMN current_focus TEXT NOT NULL DEFAULT ''")
    if project_columns and "recommended_next_step" not in project_columns:
        connection.exec_driver_sql("ALTER TABLE projects ADD COLUMN recommended_next_step TEXT NOT NULL DEFAULT ''")


def _ensure_local_timeline_phase3_schema(connection) -> None:
    """Add Phase 3 Timeline columns to existing SQLite databases."""
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(timeline_events)")}
    if columns and "project_id" not in columns:
        connection.exec_driver_sql("ALTER TABLE timeline_events ADD COLUMN project_id CHAR(36)")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_timeline_events_project_id ON timeline_events (project_id)")


def _ensure_local_learning_engine_phase4_schema(connection) -> None:
    """Add Phase 4 Learning Engine columns to existing SQLite databases."""
    columns = {row[1] for row in connection.exec_driver_sql("PRAGMA table_info(learning_observations)")}
    if columns and "source" not in columns:
        connection.exec_driver_sql("ALTER TABLE learning_observations ADD COLUMN source VARCHAR(80) NOT NULL DEFAULT 'manual'")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_learning_observations_source ON learning_observations (source)")
    if columns and "content" not in columns:
        connection.exec_driver_sql("ALTER TABLE learning_observations ADD COLUMN content TEXT NOT NULL DEFAULT ''")
    if columns and "status" not in columns:
        connection.exec_driver_sql("ALTER TABLE learning_observations ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'observed'")
        connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_learning_observations_status ON learning_observations (status)")
    if columns and "updated_at" not in columns:
        connection.exec_driver_sql("ALTER TABLE learning_observations ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")


def _ensure_local_open_loop_engine_schema(connection) -> None:
    connection.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS open_loop_actions (
            id CHAR(36) NOT NULL,
            user_id CHAR(36) NOT NULL,
            source VARCHAR(40) NOT NULL,
            source_id VARCHAR(80) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uq_open_loop_actions_source UNIQUE (user_id, source, source_id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_open_loop_actions_user_id ON open_loop_actions (user_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_open_loop_actions_source ON open_loop_actions (source)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_open_loop_actions_source_id ON open_loop_actions (source_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_open_loop_actions_status ON open_loop_actions (status)")


def _ensure_local_relationship_graph_schema(connection) -> None:
    """Allow the full continuity graph node vocabulary in existing SQLite databases."""
    rows = list(connection.exec_driver_sql("PRAGMA table_info(relationship_nodes)"))
    if not rows:
        return
    sql_rows = list(connection.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='table' AND name='relationship_nodes'"))
    table_sql = sql_rows[0][0] if sql_rows else ""
    if "open_loop" in table_sql and "conversation" in table_sql:
        return
    connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
    connection.exec_driver_sql("ALTER TABLE relationship_nodes RENAME TO relationship_nodes_old")
    connection.exec_driver_sql(
        """
        CREATE TABLE relationship_nodes (
            id CHAR(36) NOT NULL,
            user_id CHAR(36) NOT NULL,
            node_type VARCHAR(40) NOT NULL,
            entity_id CHAR(36),
            title VARCHAR(240) NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT ck_relationship_nodes_type CHECK (node_type IN ('user', 'goal', 'project', 'task', 'open_loop', 'decision', 'timeline_event', 'note', 'memory', 'conversation')),
            CONSTRAINT uq_relationship_nodes_entity UNIQUE (user_id, node_type, entity_id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    connection.exec_driver_sql(
        """
        INSERT INTO relationship_nodes (id, user_id, node_type, entity_id, title, description, created_at, updated_at)
        SELECT id, user_id, node_type, entity_id, title, description, created_at, updated_at
        FROM relationship_nodes_old
        """
    )
    connection.exec_driver_sql("DROP TABLE relationship_nodes_old")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_relationship_nodes_user_id ON relationship_nodes (user_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_relationship_nodes_node_type ON relationship_nodes (node_type)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_relationship_nodes_entity_id ON relationship_nodes (entity_id)")
    connection.exec_driver_sql("PRAGMA foreign_keys=ON")


def _ensure_local_subscription_schema(connection) -> None:
    connection.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
            id CHAR(36) NOT NULL,
            user_id CHAR(36) NOT NULL,
            plan_type VARCHAR(20) NOT NULL DEFAULT 'free',
            status VARCHAR(30) NOT NULL DEFAULT 'inactive',
            payment_status VARCHAR(30) NOT NULL DEFAULT 'none',
            provider VARCHAR(40) NOT NULL DEFAULT 'manual',
            provider_customer_id VARCHAR(120),
            provider_subscription_id VARCHAR(120),
            current_period_start DATETIME,
            current_period_end DATETIME,
            cancel_at_period_end BOOLEAN NOT NULL DEFAULT 0,
            metadata JSON NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uq_subscriptions_user_id UNIQUE (user_id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions (user_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_subscriptions_plan_type ON subscriptions (plan_type)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_subscriptions_status ON subscriptions (status)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_subscriptions_payment_status ON subscriptions (payment_status)")
    connection.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id CHAR(36) NOT NULL,
            user_id CHAR(36) NOT NULL,
            subscription_id CHAR(36),
            provider VARCHAR(40) NOT NULL DEFAULT 'razorpay',
            provider_order_id VARCHAR(120),
            provider_payment_id VARCHAR(120),
            provider_signature TEXT,
            amount FLOAT NOT NULL DEFAULT 0,
            currency VARCHAR(10) NOT NULL DEFAULT 'INR',
            status VARCHAR(30) NOT NULL DEFAULT 'created',
            plan_type VARCHAR(20) NOT NULL DEFAULT 'pro',
            metadata JSON NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE SET NULL
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_payment_transactions_user_id ON payment_transactions (user_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_payment_transactions_subscription_id ON payment_transactions (subscription_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_payment_transactions_provider_order_id ON payment_transactions (provider_order_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_payment_transactions_provider_payment_id ON payment_transactions (provider_payment_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_payment_transactions_status ON payment_transactions (status)")


def _ensure_local_notification_schema(connection) -> None:
    connection.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id CHAR(36) NOT NULL,
            user_id CHAR(36) NOT NULL,
            notification_type VARCHAR(60) NOT NULL,
            channel VARCHAR(30) NOT NULL DEFAULT 'in_app',
            title VARCHAR(160) NOT NULL,
            message TEXT NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
            priority VARCHAR(20) NOT NULL DEFAULT 'medium',
            dedupe_key VARCHAR(180) NOT NULL,
            scheduled_for DATETIME,
            sent_at DATETIME,
            read_at DATETIME,
            metadata JSON NOT NULL DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            CONSTRAINT uq_notifications_user_dedupe UNIQUE (user_id, dedupe_key),
            FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
        )
        """
    )
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notifications_notification_type ON notifications (notification_type)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notifications_channel ON notifications (channel)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notifications_status ON notifications (status)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notifications_priority ON notifications (priority)")
    connection.exec_driver_sql("CREATE INDEX IF NOT EXISTS ix_notifications_scheduled_for ON notifications (scheduled_for)")

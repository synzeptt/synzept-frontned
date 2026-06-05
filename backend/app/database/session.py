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
        await conn.run_sync(_ensure_local_knows_you_schema)
        await conn.run_sync(_ensure_local_project_intelligence_phase2_schema)
        await conn.run_sync(_ensure_local_timeline_phase3_schema)

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

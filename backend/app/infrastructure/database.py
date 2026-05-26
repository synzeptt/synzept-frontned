"""Database connectivity checks."""

import logging

from sqlalchemy import text

from app.core.config import get_settings
from app.database.session import engine
from app.database.session import SessionLocal

logger = logging.getLogger(__name__)
settings = get_settings()


async def check_database() -> bool:
    """Verify the configured database is reachable."""
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        return False


async def database_diagnostics() -> dict:
    """Lightweight database diagnostics for health and monitoring."""
    diagnostics = {"connected": False, "pool": "unknown", "migration_version": None, "dialect": "sqlite" if settings.is_sqlite else "postgresql"}
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
            diagnostics["connected"] = True
            if settings.is_sqlite:
                version_table = await session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'")
                )
                if version_table.scalar_one_or_none():
                    version = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                    diagnostics["migration_version"] = version.scalar_one_or_none()
                else:
                    diagnostics["migration_version"] = "metadata-create-all"
                return diagnostics
            version_table = await session.execute(text("SELECT to_regclass('public.alembic_version')"))
            if version_table.scalar_one_or_none():
                version = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                diagnostics["migration_version"] = version.scalar_one_or_none()
            else:
                raw_version_table = await session.execute(text("SELECT to_regclass('public.schema_migrations')"))
                if raw_version_table.scalar_one_or_none():
                    version = await session.execute(
                        text("SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1")
                    )
                    diagnostics["migration_version"] = version.scalar_one_or_none()
    except Exception as exc:
        logger.warning("Database diagnostics failed: %s", exc)
    try:
        diagnostics["pool"] = engine.pool.status()
    except Exception:
        pass
    return diagnostics


async def retrieval_diagnostics() -> dict:
    diagnostics = {
        "embeddings_table": False,
        "memories_table": False,
        "vector_extension": False,
        "recommended_indexes": {},
    }
    try:
        async with SessionLocal() as session:
            if settings.is_sqlite:
                for table in ("embeddings", "memories"):
                    result = await session.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
                        {"name": table},
                    )
                    diagnostics[f"{table}_table"] = bool(result.scalar_one_or_none())
                diagnostics["vector_extension"] = False
                diagnostics["recommended_indexes"] = {
                    "semantic_search": "disabled_for_sqlite_local_dev",
                }
                return diagnostics
            for table in ("embeddings", "memories"):
                result = await session.execute(text("SELECT to_regclass(:name)"), {"name": f"public.{table}"})
                diagnostics[f"{table}_table"] = bool(result.scalar_one_or_none())
            extension = await session.execute(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
            diagnostics["vector_extension"] = bool(extension.scalar())
            indexes = await session.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename IN ('memories', 'embeddings', 'conversations', 'tasks')
                    """
                )
            )
            present = {row.indexname for row in indexes}
            for index in (
                "ix_memories_project_updated_at",
                "ix_conversations_project_updated_at",
                "ix_tasks_project_status",
            ):
                diagnostics["recommended_indexes"][index] = index in present
    except Exception as exc:
        logger.warning("Retrieval diagnostics failed: %s", exc)
    return diagnostics

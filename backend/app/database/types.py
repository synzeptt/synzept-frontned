import uuid

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.types import CHAR, TypeDecorator


class GUID(TypeDecorator):
    """Portable UUID type for local SQLite and Postgres."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value if isinstance(value, uuid.UUID) else uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


def UUID(as_uuid: bool = True) -> GUID:
    return GUID()


JSONB = JSON


class Vector(TypeDecorator):
    """Temporary local vector storage as JSON for SQLite founder testing."""

    impl = JSON
    cache_ok = True

    def __init__(self, dimensions: int | None = None):
        super().__init__()
        self.dimensions = dimensions

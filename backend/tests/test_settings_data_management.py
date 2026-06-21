from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.models.memory import Memory
from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.auth import ProfileUpdate
from app.services.account_data_export_service import AccountDataExportService
from app.services.user_profile_service import UserProfileService


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'settings.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.mark.asyncio
async def test_profile_update_and_safe_portable_export(session_factory):
    user_id = uuid4()
    async with session_factory() as session:
        user = User(id=user_id, email="settings@example.com", password_hash="never-export-this")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserUnderstanding(user_id=user_id, category="missions", title="Mission", value="Build calmly", source="user"),
                Memory(user_id=user_id, memory_type="preferences", content="Prefers concise answers", source="conversation"),
            ]
        )
        await session.flush()

        await UserProfileService(session).update_profile(
            user,
            ProfileUpdate(display_name="Ari", profile_summary="Product builder", timezone="Asia/Kolkata"),
        )
        exported = await AccountDataExportService(session).export(user)

        assert user.display_name == "Ari"
        assert user.timezone == "Asia/Kolkata"
        assert exported["format"] == "synzept-s1-export-v1"
        assert exported["account"]["display_name"] == "Ari"
        assert "password_hash" not in exported["account"]
        assert exported["understanding"][0]["value"] == "Build calmly"
        assert exported["memories"][0]["content"] == "Prefers concise answers"

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.project import Project
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService


class _Scalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class _Result:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return _Scalars(self.values)


class _Session:
    def __init__(self):
        self.conversations = {}
        self.messages = {}
        self.projects = {}
        self.added = []

    async def get(self, model, item_id):
        stores = {
            Conversation: self.conversations,
            Message: self.messages,
            Project: self.projects,
        }
        return stores[model].get(item_id)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        now = datetime.now(timezone.utc)
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()
            if getattr(item, "created_at", None) is None:
                item.created_at = now
            item.updated_at = now
            if isinstance(item, Conversation):
                self.conversations[item.id] = item
            elif isinstance(item, Message):
                self.messages[item.id] = item
            elif isinstance(item, Project):
                self.projects[item.id] = item
        self.added = []

    async def refresh(self, item):
        item.updated_at = item.updated_at or datetime.now(timezone.utc)

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        params = statement.compile().params

        if entity is Conversation:
            rows = list(self.conversations.values())
            if "user_id_1" in params:
                rows = [row for row in rows if row.user_id == params["user_id_1"]]
            if "project_id_1" in params:
                rows = [row for row in rows if row.project_id == params["project_id_1"]]
            if "archived_at_1" not in params and "conversations.archived_at IS NULL" in str(statement):
                rows = [row for row in rows if row.archived_at is None]
            rows = [row for row in rows if row.deleted_at is None]
            rows.sort(
                key=lambda row: (
                    bool(row.pinned),
                    row.updated_at or datetime.min.replace(tzinfo=timezone.utc),
                ),
                reverse=True,
            )
            return _Result(rows)

        if entity is Message:
            rows = list(self.messages.values())
            if "conversation_id_1" in params:
                rows = [row for row in rows if row.conversation_id == params["conversation_id_1"]]
            rows.sort(key=lambda row: row.created_at)
            return _Result(rows)

        return _Result([])


def _conversation(user_id, **kwargs):
    now = kwargs.pop("created_at", datetime.now(timezone.utc))
    return Conversation(
        id=kwargs.pop("id", uuid4()),
        user_id=user_id,
        title=kwargs.pop("title", "Conversation"),
        project_id=kwargs.pop("project_id", None),
        summary=kwargs.pop("summary", None),
        conversation_type=kwargs.pop("conversation_type", "general"),
        archived_at=kwargs.pop("archived_at", None),
        created_at=now,
        updated_at=kwargs.pop("updated_at", now),
        deleted_at=kwargs.pop("deleted_at", None),
    )


@pytest.mark.asyncio
async def test_conversation_creation_supports_project_linking():
    session = _Session()
    user_id = uuid4()
    project = Project(id=uuid4(), user_id=user_id, name="Research", deleted_at=None)
    session.projects[project.id] = project

    conversation = await ConversationService(session).create(
        user_id=user_id,
        title="Project discussion",
        project_id=project.id,
        conversation_type="project",
    )

    assert conversation is not None
    assert conversation.user_id == user_id
    assert conversation.project_id == project.id
    assert conversation.conversation_type == "project"


@pytest.mark.asyncio
async def test_conversation_creation_rejects_foreign_project():
    session = _Session()
    foreign_project = Project(id=uuid4(), user_id=uuid4(), name="Other", deleted_at=None)
    session.projects[foreign_project.id] = foreign_project

    conversation = await ConversationService(session).create(user_id=uuid4(), project_id=foreign_project.id)

    assert conversation is None


@pytest.mark.asyncio
async def test_message_persistence_and_history_ordering():
    session = _Session()
    user_id = uuid4()
    conversation = _conversation(user_id)
    session.conversations[conversation.id] = conversation

    first = await MessageService(session).create(user_id, conversation.id, "user", "hello")
    second = await MessageService(session).create(user_id, conversation.id, "assistant", "hi")
    first.created_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    messages = await MessageService(session).list(user_id, conversation.id)

    assert messages == [first, second]
    assert second.metadata_ == {}


@pytest.mark.asyncio
async def test_user_isolation_blocks_foreign_conversation_messages():
    session = _Session()
    owner_id = uuid4()
    other_id = uuid4()
    conversation = _conversation(owner_id)
    session.conversations[conversation.id] = conversation

    message = await MessageService(session).create(other_id, conversation.id, "user", "nope")

    assert message is None


@pytest.mark.asyncio
async def test_archive_removes_conversation_from_default_listing():
    session = _Session()
    user_id = uuid4()
    conversation = _conversation(user_id)
    session.conversations[conversation.id] = conversation

    archived = await ConversationService(session).archive(user_id, conversation.id)
    listed = await ConversationService(session).list(user_id)
    listed_with_archived = await ConversationService(session).list(user_id, include_archived=True)

    assert archived.archived_at is not None
    assert archived.is_active is False
    assert conversation not in listed
    assert conversation in listed_with_archived


@pytest.mark.asyncio
async def test_delete_marks_conversation_deleted_and_removes_from_listing():
    session = _Session()
    user_id = uuid4()
    conversation = _conversation(user_id)
    session.conversations[conversation.id] = conversation

    deleted = await ConversationService(session).delete(user_id, conversation.id)
    listed = await ConversationService(session).list(user_id)
    listed_with_archived = await ConversationService(session).list(user_id, include_archived=True)

    assert deleted.deleted_at is not None
    assert deleted.is_active is False
    assert conversation not in listed
    assert conversation not in listed_with_archived


@pytest.mark.asyncio
async def test_pin_marks_conversation_and_keeps_it_in_list_top_of_results():
    session = _Session()
    user_id = uuid4()
    older = _conversation(user_id, updated_at=datetime.now(timezone.utc) - timedelta(days=2))
    newer = _conversation(user_id, updated_at=datetime.now(timezone.utc) - timedelta(days=1))
    session.conversations[older.id] = older
    session.conversations[newer.id] = newer

    pinned = await ConversationService(session).pin(user_id, older.id, True)
    listed = await ConversationService(session).list(user_id)

    assert pinned is not None
    assert pinned.pinned is True
    assert listed[0].id == older.id
    assert listed[1].id == newer.id


@pytest.mark.asyncio
async def test_move_conversation_to_project_updates_project_link():
    session = _Session()
    user_id = uuid4()
    project = Project(id=uuid4(), user_id=user_id, name="Research", deleted_at=None)
    conversation = _conversation(user_id)
    session.projects[project.id] = project
    session.conversations[conversation.id] = conversation

    moved = await ConversationService(session).move_to_project(user_id, conversation.id, project.id)
    assert moved is not None
    assert moved.project_id == project.id

    cleared = await ConversationService(session).move_to_project(user_id, conversation.id, None)

    assert cleared is not None
    assert conversation.project_id is None


@pytest.mark.asyncio
async def test_duplicate_conversation_copies_messages_and_project():
    session = _Session()
    user_id = uuid4()
    project = Project(id=uuid4(), user_id=user_id, name="Research", deleted_at=None)
    conversation = _conversation(user_id, title="Original", project_id=project.id, summary="A useful thread")
    session.projects[project.id] = project
    session.conversations[conversation.id] = conversation

    first = await MessageService(session).create(user_id, conversation.id, "user", "hello", metadata={"source": "test"})
    second = await MessageService(session).create(user_id, conversation.id, "assistant", "hi")
    first.created_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    duplicate = await ConversationService(session).duplicate(user_id, conversation.id)

    assert duplicate is not None
    messages = await MessageService(session).list(user_id, duplicate.id)
    assert duplicate.id != conversation.id
    assert duplicate.project_id == project.id
    assert duplicate.title == "Original copy"
    assert [message.content for message in messages] == ["hello", "hi"]
    assert messages[0].metadata_ == {"source": "test"}
    assert messages[0].conversation_id == duplicate.id
    assert messages[1].conversation_id == duplicate.id
    assert second.conversation_id == conversation.id


@pytest.mark.asyncio
async def test_streaming_placeholder_can_be_finalized():
    session = _Session()
    user_id = uuid4()
    conversation = _conversation(user_id)
    session.conversations[conversation.id] = conversation

    placeholder = await MessageService(session).create_assistant_placeholder(
        user_id,
        conversation.id,
        provider_name="openai",
        model_name="gpt-test",
    )
    final = await MessageService(session).finalize_streamed_message(
        user_id,
        placeholder.id,
        "stream complete",
        token_count=2,
    )

    assert final.content == "stream complete"
    assert final.token_count == 2
    assert final.provider_name == "openai"
    assert final.metadata_["status"] == "complete"

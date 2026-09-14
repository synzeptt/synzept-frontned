import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.mixins import TimestampMixin
from app.database.types import JSON, UUID


class ConnectedAppAccount(Base, TimestampMixin):
    __tablename__ = "connected_app_accounts"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_connected_app_user_provider"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_connected", index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_account_id: Mapped[str | None] = mapped_column(String(240), nullable=True)
    app_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    user = relationship("User")


class CalendarEvent(Base, TimestampMixin):
    __tablename__ = "calendar_events"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", "provider_event_id", name="uq_calendar_events_provider_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider_event_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    calendar_id: Mapped[str] = mapped_column(String(240), nullable=False, default="primary", index=True)
    i_cal_uid: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    recurring_event_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="confirmed", index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    location: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    all_day: Mapped[bool] = mapped_column(default=False, nullable=False)
    recurring: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    busy: Mapped[bool] = mapped_column(default=True, nullable=False)
    html_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    account = relationship("ConnectedAppAccount")


class GoogleTaskList(Base, TimestampMixin):
    __tablename__ = "google_task_lists"
    __table_args__ = (UniqueConstraint("user_id", "provider_list_id", name="uq_google_task_lists_provider_list"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_list_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GoogleTask(Base, TimestampMixin):
    __tablename__ = "google_tasks"
    __table_args__ = (UniqueConstraint("user_id", "provider_task_id", name="uq_google_tasks_provider_task"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    task_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("google_task_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_task_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    provider_parent_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="needsAction", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    position: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class GoogleContact(Base, TimestampMixin):
    __tablename__ = "google_contacts"
    __table_args__ = (UniqueConstraint("user_id", "resource_name", name="uq_google_contacts_resource_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    etag: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    display_name: Mapped[str] = mapped_column(String(300), nullable=False, default="", index=True)
    emails: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    company: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    job_title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    relationship_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class MicrosoftMailMessage(Base, TimestampMixin):
    __tablename__ = "microsoft_mail_messages"
    __table_args__ = (UniqueConstraint("user_id", "provider_message_id", name="uq_microsoft_mail_message"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_message_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    conversation_id: Mapped[str] = mapped_column(String(512), nullable=False, default="", index=True)
    sender_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    sender_email: Mapped[str] = mapped_column(String(320), nullable=False, default="", index=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    folder_id: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    categories: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class MicrosoftDriveItem(Base, TimestampMixin):
    __tablename__ = "microsoft_drive_items"
    __table_args__ = (UniqueConstraint("user_id", "provider_item_id", name="uq_microsoft_drive_item"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_item_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    mime_type: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    shared: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class MicrosoftTaskList(Base, TimestampMixin):
    __tablename__ = "microsoft_task_lists"
    __table_args__ = (UniqueConstraint("user_id", "provider_list_id", name="uq_microsoft_task_list"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_list_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")


class MicrosoftTask(Base, TimestampMixin):
    __tablename__ = "microsoft_tasks"
    __table_args__ = (UniqueConstraint("user_id", "provider_task_id", name="uq_microsoft_task"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    task_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("microsoft_task_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_task_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="notStarted", index=True)
    importance: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recurrence: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class MicrosoftContact(Base, TimestampMixin):
    __tablename__ = "microsoft_contacts"
    __table_args__ = (UniqueConstraint("user_id", "provider_contact_id", name="uq_microsoft_contact"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_contact_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False, default="", index=True)
    emails: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    company: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    job_title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    relationship_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class GitHubRepository(Base, TimestampMixin):
    __tablename__ = "github_repositories"
    __table_args__ = (UniqueConstraint("user_id", "provider_repository_id", name="uq_github_repository"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_repository_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(256), nullable=False, default="", index=True)
    full_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", index=True)
    visibility: Mapped[str] = mapped_column(String(40), nullable=False, default="private")
    default_branch: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    repository_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class GitHubIssue(Base, TimestampMixin):
    __tablename__ = "github_issues"
    __table_args__ = (UniqueConstraint("repository_id", "number", name="uq_github_issue"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("github_repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN", index=True)
    labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    assignees: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    provider_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GitHubPullRequest(Base, TimestampMixin):
    __tablename__ = "github_pull_requests"
    __table_args__ = (UniqueConstraint("repository_id", "number", name="uq_github_pull_request"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("github_repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN", index=True)
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    merged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    review_status: Mapped[str] = mapped_column(String(80), nullable=False, default="review_required", index=True)
    review_count: Mapped[int] = mapped_column(nullable=False, default=0)
    provider_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GitHubCommit(Base, TimestampMixin):
    __tablename__ = "github_commits"
    __table_args__ = (UniqueConstraint("repository_id", "sha", name="uq_github_commit"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("github_repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    sha: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    author_login: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class GitHubRelease(Base, TimestampMixin):
    __tablename__ = "github_releases"
    __table_args__ = (UniqueConstraint("repository_id", "provider_release_id", name="uq_github_release"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("github_repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_release_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    tag_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prerelease: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class SlackChannel(Base, TimestampMixin):
    __tablename__ = "slack_channels"
    __table_args__ = (UniqueConstraint("user_id", "provider_channel_id", name="uq_slack_channel"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_channel_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    channel_type: Mapped[str] = mapped_column(String(40), nullable=False, default="channel", index=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_member: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    member_count: Mapped[int] = mapped_column(nullable=False, default=0)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class SlackUser(Base, TimestampMixin):
    __tablename__ = "slack_users"
    __table_args__ = (UniqueConstraint("user_id", "provider_user_id", name="uq_slack_user"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False, default="", index=True)
    real_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class SlackConversationActivity(Base, TimestampMixin):
    __tablename__ = "slack_conversation_activities"
    __table_args__ = (UniqueConstraint("channel_id", "provider_message_ts", name="uq_slack_activity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("slack_channels.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_message_ts: Mapped[str] = mapped_column(String(64), nullable=False)
    author_provider_user_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", index=True)
    thread_ts: Mapped[str] = mapped_column(String(64), nullable=False, default="", index=True)
    reply_count: Mapped[int] = mapped_column(nullable=False, default=0)
    mention_user_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    participant_user_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    signal_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    is_direct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)


class MicrosoftTeam(Base, TimestampMixin):
    __tablename__ = "microsoft_teams"
    __table_args__ = (UniqueConstraint("user_id", "provider_team_id", name="uq_microsoft_team"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_team_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class MicrosoftTeamChannel(Base, TimestampMixin):
    __tablename__ = "microsoft_team_channels"
    __table_args__ = (UniqueConstraint("team_id", "provider_channel_id", name="uq_microsoft_team_channel"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("microsoft_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_channel_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    membership_type: Mapped[str] = mapped_column(String(40), nullable=False, default="standard")
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)


class MicrosoftTeamMembership(Base, TimestampMixin):
    __tablename__ = "microsoft_team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "provider_user_id", name="uq_microsoft_team_membership"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("microsoft_teams.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(300), nullable=False, default="", index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, default="")
    roles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class MicrosoftTeamsActivity(Base, TimestampMixin):
    __tablename__ = "microsoft_teams_activities"
    __table_args__ = (UniqueConstraint("user_id", "provider_activity_id", name="uq_microsoft_teams_activity"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("microsoft_teams.id", ondelete="CASCADE"), nullable=True, index=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("microsoft_team_channels.id", ondelete="CASCADE"), nullable=True, index=True)
    provider_activity_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    activity_type: Mapped[str] = mapped_column(String(40), nullable=False, default="channel_message", index=True)
    author_provider_user_id: Mapped[str] = mapped_column(String(512), nullable=False, default="", index=True)
    author_display_name: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    reply_to_id: Mapped[str] = mapped_column(String(512), nullable=False, default="", index=True)
    mention_user_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    participant_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    signal_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    activity_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)


class NotionResource(Base, TimestampMixin):
    __tablename__ = "notion_resources"
    __table_args__ = (UniqueConstraint("user_id", "provider_resource_id", name="uq_notion_resource"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connected_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("connected_app_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_resource_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False, default="", index=True)
    parent_provider_id: Mapped[str] = mapped_column(String(128), nullable=False, default="", index=True)
    parent_type: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    provider_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    resource_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.jobs import JobType, enqueue
from app.services.action_execution_service import ActionExecutionService


class ConnectedAppActionPreparationService:
    """Turns connected-app sync signals into prepared AI work requests."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.action_service = ActionExecutionService(session)

    async def prepare_for_provider(
        self,
        user_id: UUID,
        provider: str,
        observations_created: int,
        *,
        account_metadata: dict | None = None,
    ) -> int:
        if observations_created <= 0:
            return 0

        messages = self._messages_for_provider(provider, account_metadata=account_metadata)
        created = 0
        for message in messages:
            action = await self.action_service.create_for_request(
                user_id=user_id,
                conversation_id=None,
                project_id=None,
                message=message,
                metadata={"source": "connected_app", "provider": provider},
            )
            if action and action.status == "queued":
                enqueue(JobType.ACTION_EXECUTE, action_id=action.id)
                created += 1
        return created

    def _messages_for_provider(self, provider: str, *, account_metadata: dict | None = None) -> list[str]:
        if provider in {"google_calendar", "microsoft_outlook_calendar"}:
            upcoming_meetings = account_metadata.get("upcoming_meetings") if account_metadata else None
            if upcoming_meetings:
                return [
                    "Prepare a concise meeting briefing for the next calendar events below. Include objectives, decisions needed, risks, conflicts, and one clear next action.\n\n"
                    "Upcoming meetings:\n"
                    f"{self._format_meetings_for_prompt(upcoming_meetings)}",
                ]

            return [
                "Prepare a concise briefing for my upcoming meetings and highlight any scheduling risks, conflicts, or travel patterns from my latest calendar activity.",
            ]

        if provider == "slack":
            if account_metadata:
                blocker_signals = int(account_metadata.get("blocker_signal_count") or 0)
                decision_signals = int(account_metadata.get("decision_pending_count") or 0)
                if blocker_signals or decision_signals:
                    return [
                        "Summarize recent Slack signals around blockers, pending decisions, and active collaboration so I can identify the most important follow-up work.",
                    ]
                direct_mentions = int(account_metadata.get("direct_mention_count") or 0)
                if direct_mentions:
                    return [
                        "Summarize recent Slack mentions and collaboration activity so I can turn it into useful follow-up work.",
                    ]
            return [
                "Summarize recent Slack collaboration and active work signals so I can understand the most important follow-up items.",
            ]

        if provider == "github":
            if account_metadata:
                open_prs = int(account_metadata.get("open_pull_requests_count") or 0)
                open_issues = int(account_metadata.get("open_issues_count") or 0)
                if open_prs or open_issues:
                    return [
                        "Summarize active GitHub engineering work and highlight long-running pull requests, open issues, and review signals.",
                    ]
            return [
                "Summarize recent GitHub repository signals and highlight the active engineering work that matters most.",
            ]

        if provider == "notion":
            return [
                "Draft a short review of recently updated Notion pages and databases, highlighting any follow-up actions or active knowledge work.",
            ]

        if provider == "microsoft_teams":
            return [
                "Summarize recent Microsoft Teams collaboration signals for blockers, pending decisions, and active conversations.",
            ]

        if provider == "microsoft_outlook_mail":
            return [
                "Summarize current Outlook mailbox activity and identify the messages most likely needing follow-up.",
            ]

        if provider == "microsoft_todo":
            return [
                "Summarize open Microsoft To Do tasks and overdue work so I can focus on the most important follow-ups.",
            ]

        if provider == "microsoft_onedrive":
            return [
                "Summarize recent OneDrive file activity and highlight active files or stale documents that need attention.",
            ]

        return [
            "Summarize recent connected app signals and highlight the most useful follow-up work from this data.",
        ]

    @staticmethod
    def _format_meetings_for_prompt(upcoming_meetings: list[dict]) -> str:
        lines: list[str] = []
        for meeting in upcoming_meetings[:4]:
            start = meeting.get("startAt")
            end = meeting.get("endAt")
            title = meeting.get("title") or "Untitled meeting"
            people = meeting.get("people") or []
            people_text = ", ".join(person.get("name") or person.get("email") or "attendee" for person in people[:3])
            when = f"{start:%Y-%m-%d %H:%M} to {end:%H:%M}" if start and end else "unspecified time"
            line = f"- {when}: {title}. Participants: {people_text or 'unknown'}."
            lines.append(line)
        return "\n".join(lines)

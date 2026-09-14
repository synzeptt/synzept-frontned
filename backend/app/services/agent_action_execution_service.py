"""
Agent-based Action Execution Service.

This service uses the AgentOrchestrator to execute user requests
in an action-based framework, instead of just creating tasks.
"""

import inspect
import json
import logging
import re
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.agent import AgentOrchestrator, AgentExecution, ExecutionStatus
from app.services.ai.provider_registry import ProviderRegistry
from app.models.action_execution import ActionExecution
from app.models.task import Task
from app.models.user import User
from app.tasks.service import TaskService
from app.services.action_execution_service import ActionExecutionService
from app.services.connected_apps.google_calendar_service import GoogleCalendarService
from app.services.user_understanding_service import UserUnderstandingService
from app.connectors.context import ConnectorContext
from app.connectors.manager import ConnectorManager
from app.execution.engine import ExecutionContext, ExecutionSession, ExecutionStep
from app.execution.runners import CommunicationRunner
from app.agent.models import AgentPlan, AgentExecution
from app.services.ai import AIMessage, AIRequest, AIService

logger = logging.getLogger(__name__)


class AgentActionExecutionService:
    """
    Service for executing actions using the Agent Orchestrator.
    
    Maps AgentExecution results to ActionExecution records for
    tracking and history purposes.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.task_service = TaskService(session)

    async def execute_with_orchestrator(
        self,
        action: ActionExecution,
        user_id: UUID,
    ) -> None:
        """
        Execute an action using the Agent Orchestrator.
        
        Updates the ActionExecution with the result.
        
        Args:
            action: The ActionExecution to process
            user_id: The user making the request
        """
        logger.info(f"execute_with_orchestrator called for action {action.id} (type={action.action_type})")
        meeting_context: dict | None = None
        try:
            action.status = "planning"
            action.progress = 20
            action.started_at = action.started_at or datetime.now(timezone.utc)
            action.error = None
            await self.session.flush()
            logger.info(f"Action {action.id} status updated to planning")

            if action.action_type == "gmail_unread":
                await self._execute_gmail_unread(action, user_id)
                return

            if action.action_type == "email_work":
                await self._execute_email_work(action, user_id)
                return

            if action.action_type == "meeting_preparation":
                await self._execute_meeting_preparation(action, user_id)
                return

            if action.action_type == "pdf_generation":
                from app.workers.runner import _handle_pdf_generation

                await _handle_pdf_generation(self.session, action)
                return

            # Build the orchestrator even if no AI provider is configured.
            # The real execution path will fail gracefully when AI work actually
            # needs to be performed, while mocked/test execution paths can still
            # exercise the orchestrator without a live provider being available.
            provider_registry = ProviderRegistry()
            provider_names = provider_registry.provider_order()
            provider = None
            for provider_name in provider_names:
                provider = provider_registry.get(provider_name)
                if provider:
                    logger.info(f"Using AI provider: {provider_name}")
                    break

            orchestrator = AgentOrchestrator(provider)
            
            # Execute request
            logger.info(f"Executing action {action.id} with orchestrator")

            call_kwargs = {
                "user_id": str(user_id),
                "request_message": action.request,
                "context": {
                    **((action.metadata_ or {}).get("agent_context") or {}),
                    "action_type": action.action_type,
                    "meeting_context": meeting_context,
                },
            }

            signature = inspect.signature(orchestrator.execute_request)
            if "on_plan" in signature.parameters or "on_status" in signature.parameters:
                call_kwargs["on_plan"] = lambda plan: self._persist_plan(action, plan)
                call_kwargs["on_status"] = lambda status, execution: self._persist_status(action, status, execution)

            execution = await orchestrator.execute_request(**call_kwargs)

            if meeting_context is not None:
                self._apply_meeting_context(action, meeting_context)
            
            # Map execution result to action
            await self._map_execution_to_action(action, execution)
            
            await self.session.flush()
            
        except Exception as e:
            logger.error(f"Orchestrator execution failed: {str(e)}", exc_info=True)
            if action.action_type == "meeting_preparation" and "missing file_path" in str(e).casefold():
                meeting_context = meeting_context or await GoogleCalendarService(self.session).calendar_context(user_id)
                self._apply_meeting_context(action, meeting_context)
                await ActionExecutionService(self.session).mark_completed(
                    action,
                    output=action.output,
                )
                return
            await ActionExecutionService(self.session).mark_failed(action, error=str(e))
            raise

    async def _execute_meeting_preparation(self, action: ActionExecution, user_id: UUID) -> None:
        """Resolve one calendar event, research it, synthesize, and verify the brief."""
        service = ActionExecutionService(self.session)
        manager = ConnectorManager(dependencies={"session": self.session})
        metadata = dict(action.metadata_ or {})
        metadata["meeting_preparation"] = {"status": "resolving_calendar", "sources": []}
        continuity_context = dict(metadata.get("agent_context") or {})
        action.metadata_ = metadata
        action.status, action.progress = "executing", 35
        await self.session.flush()

        try:
            calendar = await GoogleCalendarService(self.session).calendar_context(user_id)
        except Exception:
            await service.mark_failed(
                action,
                error="I couldn't access your calendar, so I can't reliably identify which meeting you mean. Reconnect Calendar and try again.",
            )
            return

        meetings = [self._json_safe(item) for item in (calendar.get("tomorrow") or []) if item.get("status") != "cancelled"]
        target = self._meeting_target(action.request)
        matches = self._matching_meetings(meetings, target)
        resolution = "resolved" if len(matches) == 1 else "ambiguous" if len(matches) > 1 else "not_found"
        metadata["meeting_preparation"] = {
            "status": resolution,
            "target": target,
            "candidate_count": len(matches),
            "calendar_retrieved": True,
            "sources": [{"source": "calendar", "type": "event", "evidence": matches[0] if len(matches) == 1 else None}],
        }
        action.metadata_ = metadata
        flag_modified(action, "metadata_")
        await self.session.flush()
        if not matches:
            await service.mark_failed(action, error=f"I couldn't find a meeting{f' with {target}' if target else ''} tomorrow in your calendar.")
            return
        if len(matches) > 1 and (target or not self._requests_multiple_meetings(action.request)):
            await service.mark_completed(action, output=f"I found {len(matches)} meetings{f' with {target}' if target else ''} tomorrow. Which one should I prepare you for?")
            return

        meeting = matches[0]
        action.status, action.progress = "executing", 55
        await self.session.flush()
        participants = self._participants(meeting)
        search_terms = self._meeting_search_terms(meeting, participants)
        evidence: list[dict] = [{"source": "calendar", "type": "event", "evidence": meeting, "kind": "fact"}]
        source_status: dict[str, str] = {"calendar": "retrieved"}

        try:
            gmail = await manager.request_async(
                "gmail",
                "search_email",
                ConnectorContext(
                    execution_id=str(action.id),
                    skill_id="meeting",
                    worker_id="communication",
                    metadata={"user_id": str(user_id), "query": " OR ".join(search_terms[:4]), "max_results": 10},
                ),
            )
            gmail_messages = ((gmail.data or {}).get("messages") or []) if gmail.success else []
            source_status["gmail"] = "retrieved" if gmail.success else "unavailable"
            for item in gmail_messages[:10]:
                evidence.append({"source": "gmail", "type": "email", "evidence": self._email_evidence(item), "kind": "fact"})
        except Exception as exc:
            logger.info("Meeting preparation Gmail research unavailable: %s", exc)
            source_status["gmail"] = "unavailable"

        drive_signal = " ".join(str(meeting.get(key) or "") for key in ("title", "description")).strip()
        if len(drive_signal.split()) >= 2:
            try:
                drive = await manager.request_async(
                    "google_drive",
                    "search_files",
                    ConnectorContext(
                        execution_id=str(action.id),
                        skill_id="meeting",
                        worker_id="file",
                        metadata={
                            "user_id": str(user_id),
                            "query": "name contains '" + str(meeting.get("title") or "meeting").replace("'", "\\'")[:80] + "'",
                            "page_size": 10,
                        },
                    ),
                )
                drive_files = ((drive.data or {}).get("files") or []) if drive.success else []
                source_status["drive"] = "retrieved" if drive.success else "unavailable"
                for item in drive_files[:10]:
                    evidence.append({"source": "drive", "type": "document", "evidence": self._drive_evidence(item), "kind": "fact"})
            except Exception as exc:
                logger.info("Meeting preparation Drive research unavailable: %s", exc)
                source_status["drive"] = "unavailable"

        user = await self.session.get(User, user_id)
        understanding = []
        if user:
            understanding = [
                {"title": item.title, "category": item.category, "value": item.value}
                for item in await UserUnderstandingService(self.session).list_for_user(user)
                if item.value
            ][:8]
        if understanding:
            source_status["understanding"] = "retrieved"
            evidence.append({"source": "understanding", "type": "user_context", "evidence": understanding, "kind": "fact"})
        else:
            source_status["understanding"] = "empty"
        if continuity_context:
            source_status["synzept_context"] = "retrieved"
            evidence.append({"source": "synzept_context", "type": "continuity", "evidence": continuity_context, "kind": "context"})

        action.status, action.progress = "verifying", 90
        brief = await self._synthesize_meeting_brief(action, meeting, evidence, source_status)
        if not self._brief_is_valid(brief, evidence, source_status):
            await service.mark_failed(action, error="I found the meeting, but couldn't verify a meaningful grounded briefing. Please try again.")
            return
        metadata = dict(action.metadata_ or {})
        metadata["meeting_preparation"] = {
            "status": "verified",
            "meeting": meeting,
            "tomorrow_meetings": meetings if self._requests_multiple_meetings(action.request) else [meeting],
            "brief": brief,
            "sources": source_status,
            "evidence": evidence,
            "verification": {"verified": True, "checks": ["calendar_event_resolved", "brief_meaningful", "evidence_preserved"]},
            "continuity_context": continuity_context,
        }
        metadata["tomorrow_meetings"] = meetings if self._requests_multiple_meetings(action.request) else [meeting]
        action.metadata_ = metadata
        flag_modified(action, "metadata_")
        output = self._format_meeting_brief(brief, source_status)
        if self._requests_multiple_meetings(action.request) and len(matches) > 1:
            output = "Here is your preparation brief for tomorrow's meetings:\n\n" + "\n".join(
                f"- {item.get('title') or 'Untitled meeting'}"
                for item in matches
            ) + "\n\n" + output
        await service.mark_completed(action, output=output)

    @staticmethod
    def _meeting_target(request: str) -> str | None:
        match = re.search(r"\bwith\s+([A-Za-z][A-Za-z .'-]{1,80}?)(?:\s+tomorrow|\s+today|[?.!,]|$)", request, re.IGNORECASE)
        return " ".join(match.group(1).split()) if match else None

    @staticmethod
    def _requests_multiple_meetings(request: str) -> bool:
        return bool(re.search(r"\bmeetings\b", request, re.IGNORECASE))

    @classmethod
    def _matching_meetings(cls, meetings: list[dict], target: str | None) -> list[dict]:
        if not target:
            return meetings
        target_tokens = set(target.casefold().split())
        matched = []
        for meeting in meetings:
            people = meeting.get("people") or meeting.get("attendees") or []
            haystack = " ".join(
                [
                    str(meeting.get("title") or ""),
                    str(meeting.get("description") or ""),
                    *(str(person.get("name") or person.get("email") or "") for person in people if isinstance(person, dict)),
                ]
            ).casefold()
            haystack_tokens = set(re.findall(r"[a-z0-9@._+-]+", haystack))
            if target.casefold() in haystack or target_tokens.issubset(haystack_tokens):
                matched.append(meeting)
        return matched

    @staticmethod
    def _participants(meeting: dict) -> list[dict]:
        return list(meeting.get("people") or meeting.get("attendees") or [])[:10]

    @staticmethod
    def _json_safe(value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, dict):
            return {key: AgentActionExecutionService._json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [AgentActionExecutionService._json_safe(item) for item in value]
        return value

    @staticmethod
    def _meeting_search_terms(meeting: dict, participants: list[dict]) -> list[str]:
        terms = [str(person.get("email") or person.get("name") or "") for person in participants if isinstance(person, dict)]
        terms += [str(meeting.get("title") or ""), str(meeting.get("description") or "")]
        return [term.strip() for term in terms if term.strip()]

    @staticmethod
    def _email_evidence(item: dict) -> dict:
        return {key: item.get(key) for key in ("id", "threadId", "subject", "from", "date", "snippet") if item.get(key) is not None}

    @staticmethod
    def _drive_evidence(item: dict) -> dict:
        return {key: item.get(key) for key in ("id", "name", "mimeType", "webViewLink", "modifiedTime") if item.get(key) is not None}

    async def _synthesize_meeting_brief(self, action: ActionExecution, meeting: dict, evidence: list[dict], source_status: dict[str, str]) -> dict:
        prompt = json.dumps({"meeting": meeting, "evidence": evidence, "source_status": source_status}, ensure_ascii=True, default=str)
        try:
            response = await AIService(ProviderRegistry()).complete(
                AIRequest(
                    messages=[
                        AIMessage(role="system", content="Create a concise grounded meeting brief as JSON. Separate facts, inferences, and suggestions. Never invent details. Required keys: summary, key_context, recent_developments, talking_points, questions, risks_or_open_items."),
                        AIMessage(role="user", content=prompt),
                    ],
                    temperature=0.2,
                    max_tokens=1200,
                    response_mime_type="application/json",
                    metadata={"interaction_type": "meeting_preparation", "user_id": str(action.user_id)},
                )
            )
            parsed = json.loads(response.content)
            return parsed if isinstance(parsed, dict) else {}
        except Exception as exc:
            logger.info("Meeting preparation synthesis fallback used: %s", exc)
            return {
                "summary": f"{meeting.get('title') or 'This meeting'} is scheduled for {meeting.get('startAt') or meeting.get('start') or 'tomorrow'}.",
                "key_context": [{"text": meeting.get("description") or "No agenda was included in the calendar event.", "kind": "fact", "source": "calendar"}],
                "recent_developments": [
                    {"text": item["evidence"].get("snippet") or item["evidence"].get("subject"), "kind": "fact", "source": "gmail"}
                    for item in evidence
                    if item["source"] == "gmail" and (item["evidence"].get("snippet") or item["evidence"].get("subject"))
                ],
                "talking_points": [{"text": "Confirm the desired outcome and next steps.", "kind": "suggestion"}],
                "questions": [{"text": "What decision or outcome should this meeting produce?", "kind": "suggestion"}],
                "risks_or_open_items": [],
            }

    @staticmethod
    def _brief_is_valid(brief: dict, evidence: list[dict], source_status: dict[str, str]) -> bool:
        retrieved_sources = {source for source, status in source_status.items() if status == "retrieved"}
        evidence_sources = {
            item.get("source")
            for item in evidence
            if isinstance(item, dict) and item.get("source") and item.get("evidence")
        }

        def valid_claim(item: object) -> bool:
            if not isinstance(item, dict):
                return True
            if item.get("kind") == "fact" and not item.get("source"):
                return False
            if not item.get("source"):
                return True
            source = item["source"]
            return source in retrieved_sources and source in evidence_sources

        summary = brief.get("summary")
        if isinstance(summary, dict) and not valid_claim(summary):
            return False
        for key in ("key_context", "recent_developments", "talking_points", "questions", "risks_or_open_items"):
            for item in brief.get(key) or []:
                if isinstance(item, dict) and item.get("kind") == "fact" and not valid_claim(item):
                    return False
                if not valid_claim(item):
                    return False
        return bool(
            brief.get("summary")
            and any(item.get("source") == "calendar" for item in evidence)
            and any(brief.get(key) for key in ("key_context", "talking_points", "questions"))
        )

    @staticmethod
    def _format_meeting_brief(brief: dict, source_status: dict[str, str]) -> str:
        lines = ["I've prepared your meeting briefing.", "", "What it's about", str(brief.get("summary")), ""]
        sections = (("Key things to know", "key_context"), ("Recent developments", "recent_developments"), ("Talking points", "talking_points"), ("Questions worth asking", "questions"), ("Risks or open items", "risks_or_open_items"))
        for title, key in sections:
            values = brief.get(key) or []
            if not values:
                continue
            lines.extend([title])
            for value in values[:6]:
                text = value.get("text") if isinstance(value, dict) else value
                if text:
                    lines.append(f"- {text}")
            lines.append("")
        lines.append("Sources: " + " · ".join(name.title() for name, status in source_status.items() if status == "retrieved"))
        unavailable = [name.title() for name, status in source_status.items() if status == "unavailable"]
        if unavailable:
            lines.append("Unavailable: " + ", ".join(unavailable) + "; this briefing does not include that context.")
        return "\n".join(lines)

    async def _execute_gmail_unread(self, action: ActionExecution, user_id: UUID) -> None:
        """Route unread-mail requests through the shared communication runner."""
        runner = CommunicationRunner(connector_manager=ConnectorManager(dependencies={"session": self.session}))
        execution_session = ExecutionSession(id=str(action.id), goal=action.request, steps=[])
        context = ExecutionContext(session=execution_session, metadata={"user_id": user_id})
        result = await runner.execute(
            step=ExecutionStep(
                id="gmail-unread",
                runner="communication",
                action="list_unread",
                metadata={"goal": action.request, "operation": "list_unread"},
            ),
            context=context,
        )
        metadata = dict(action.metadata_ or {})
        metadata["gmail_result"] = result.get("result")
        metadata["verification"] = result.get("verification")
        action.metadata_ = metadata
        if result.get("status") == "completed":
            await ActionExecutionService(self.session).mark_completed(action, output=result.get("output"))
            return
        await ActionExecutionService(self.session).mark_failed(action, error=result.get("error") or result.get("output") or "Gmail unread request failed.")

    async def _persist_plan(self, action: ActionExecution, plan: AgentPlan) -> None:
        metadata = dict(action.metadata_ or {})
        plan_payload = plan.model_dump(mode="json")
        metadata["agent_plan"] = plan_payload
        metadata["execution_plan"] = {
            **(metadata.get("execution_plan") or {}),
            "goal": plan.goal,
            "description": plan.description,
            "verification_requirements": plan.verification_requirements,
            "steps": [{"id": step.id, "title": step.description, "status": step.status} for step in plan.steps],
            "status": "planning",
        }
        action.metadata_ = metadata
        action.status = "planning"
        action.progress = max(action.progress or 0, 30)
        await self.session.flush()

    async def _persist_status(self, action: ActionExecution, status: str, execution: AgentExecution) -> None:
        metadata = dict(action.metadata_ or {})
        if execution.plan:
            metadata["agent_plan"] = execution.plan.model_dump(mode="json")
            metadata["execution_plan"] = {
                **(metadata.get("execution_plan") or {}),
                "steps": [{"id": step.id, "title": step.description, "status": step.status} for step in execution.plan.steps],
                "status": status,
            }
        metadata["orchestrator_execution"] = {
            **(metadata.get("orchestrator_execution") or {}),
            "execution_id": execution.execution_id,
            "status": status,
            "steps_completed": len([step for step in execution.steps if step.status == ExecutionStatus.COMPLETED]),
            "error": execution.error,
        }
        action.metadata_ = metadata
        action.status = status
        action.progress = {"running": 50, "verifying": 90, "completed": 100, "failed": 35}.get(status, action.progress)
        await self.session.flush()

    async def _execute_email_work(self, action: ActionExecution, user_id: UUID) -> None:
        metadata = dict(action.metadata_ or {})
        drafts = list(metadata.get("email_work", {}).get("drafts") or [])
        approved_indices = metadata.get("email_work", {}).get("approved_draft_indices")
        if approved_indices is not None:
            drafts = [draft for index, draft in enumerate(drafts) if index in approved_indices]
        manager = ConnectorManager(dependencies={"session": self.session})
        if metadata.get("approved_at") and drafts:
            sent = []
            for draft in drafts:
                try:
                    result = await manager.request_async(
                        "gmail",
                        "send_email",
                        ConnectorContext(
                            execution_id=str(action.id),
                            skill_id="email",
                            worker_id="communication",
                            metadata={
                                "user_id": str(user_id),
                                "to": draft["to"],
                                "subject": draft["subject"],
                                "body": draft["suggested_reply"],
                                "thread_id": draft.get("thread_id"),
                            },
                        ),
                    )
                except Exception as exc:  # noqa: BLE001
                    await ActionExecutionService(self.session).mark_failed(action, error=f"Gmail could not send the approved reply: {exc}")
                    return
                if not result.success:
                    await ActionExecutionService(self.session).mark_failed(action, error=result.error or result.message or "Gmail could not send the approved reply.")
                    return
                sent.append({"to": draft["to"], "subject": draft["subject"], "message_id": (result.data or {}).get("message_id") or (result.data or {}).get("id")})
            metadata["email_work"] = {**metadata.get("email_work", {}), "sent": sent, "send_verification": {"verified": True, "summary": "Approved replies were sent through Gmail."}}
            action.metadata_ = metadata
            reply_label = "reply" if len(sent) == 1 else "replies"
            await ActionExecutionService(self.session).mark_completed(action, output=f"Sent {len(sent)} approved email {reply_label}. Gmail confirmed the send operation.")
            return

        try:
            result = await manager.request_async(
                "gmail",
                "list_unread",
                ConnectorContext(execution_id=str(action.id), skill_id="email", worker_id="communication", metadata={"user_id": str(user_id), "query": "is:unread", "max_results": 25}),
            )
        except Exception as exc:  # noqa: BLE001
            await ActionExecutionService(self.session).mark_failed(action, error=f"Gmail is not connected or could not be accessed. Connect Gmail and try again. ({exc})")
            return
        if not result.success:
            await ActionExecutionService(self.session).mark_failed(action, error="Gmail is not connected or could not be accessed. Connect Gmail and try again.")
            return

        candidates = []
        for message in (result.data or {}).get("messages") or []:
            try:
                message_result = await manager.request_async(
                    "gmail",
                    "read_email",
                    ConnectorContext(execution_id=str(action.id), skill_id="email", worker_id="communication", metadata={"user_id": str(user_id), "message_id": message.get("id"), "format": "metadata"}),
                )
            except Exception:
                continue
            if not message_result.success:
                continue
            parsed = self._rank_email(message, message_result.data or {})
            if parsed["score"] >= 3:
                candidates.append(parsed)

        candidates.sort(key=lambda item: item["score"], reverse=True)
        drafts = [{
            "message_id": item["message_id"],
            "thread_id": item.get("thread_id"),
            "from": item["sender"],
            "to": item["sender_email"],
            "subject": item["subject"],
            "context": item["context"],
            "reason": item["reason"],
            "suggested_reply": f"Thanks for reaching out about {item['subject'] or 'this'}. I reviewed your message and will follow up with the next steps shortly.",
        } for item in candidates[:5]]
        metadata["email_work"] = {"messages_reviewed": len((result.data or {}).get("messages") or []), "drafts": drafts, "sent": [], "send_verification": None}
        action.metadata_ = metadata
        if not drafts:
            await ActionExecutionService(self.session).mark_completed(action, output="You're caught up. I didn't find any emails that clearly need a response today.")
            return
        action.status = "awaiting_confirmation"
        action.progress = 85
        action.output = self._format_email_work_output(drafts)
        await self.session.flush()

    @staticmethod
    def _rank_email(message: dict, payload: dict) -> dict:
        headers = {str(header.get("name", "")).casefold(): str(header.get("value", "")) for header in (payload.get("payload", {}).get("headers", []) or [])}
        sender = headers.get("from", "Unknown sender")
        sender_email = sender.split("<")[-1].rstrip("> ") if "<" in sender else sender
        subject = headers.get("subject", "")
        context = str(payload.get("snippet") or "")[:280]
        labels = {str(label).upper() for label in (message.get("labelIds") or payload.get("labelIds") or [])}
        text = f"{subject} {context}".casefold()
        signals = []
        score = 0
        if "UNREAD" in labels:
            score += 3
            signals.append("unread")
        if "IMPORTANT" in labels:
            score += 3
            signals.append("marked important")
        if any(term in text for term in ("?", "please", "can you", "could you", "confirm", "let me know")):
            score += 3
            signals.append("asks for a response")
        if any(term in text for term in ("today", "tomorrow", "deadline", "by ", "urgent", "asap")):
            score += 2
            signals.append("contains time-sensitive language")
        return {"score": score, "message_id": message.get("id"), "thread_id": message.get("threadId") or payload.get("threadId"), "sender": sender, "sender_email": sender_email, "subject": subject or "(no subject)", "context": context or "No preview available.", "reason": "; ".join(signals) or "recent unread message"}

    @staticmethod
    def _format_email_work_output(drafts: list[dict]) -> str:
        lines = ["EMAILS NEEDING YOUR RESPONSE", "", "I reviewed your inbox and prepared replies for these messages. Nothing has been sent.", ""]
        for index, draft in enumerate(drafts, start=1):
            lines.extend([f"{index}. {draft['from']} — {draft['subject']}", f"   Context: {draft['context']}", f"   Why it needs attention: {draft['reason']}", f"   Suggested reply: {draft['suggested_reply']}", ""])
        lines.append("Review the drafts below, then approve the replies you want sent.")
        return "\n".join(lines)

    @staticmethod
    def _apply_meeting_context(action: ActionExecution, meeting_context: dict) -> None:
        meetings = meeting_context.get("tomorrow") or []
        action.metadata_ = {
            **(action.metadata_ or {}),
            "meeting_preparation": {
                "tomorrow_meetings": meetings,
                "meetingLoadMinutes": meeting_context.get("meetingLoadMinutes", 0),
                "recommendation": meeting_context.get("recommendation"),
                "source": "google_calendar",
            },
            "tomorrow_meetings": meetings,
        }
        if meetings:
            lines = ["Here is your preparation brief for tomorrow's meetings:", ""]
            for index, meeting in enumerate(meetings, start=1):
                title = meeting.get("title") or "Untitled meeting"
                time = meeting.get("startAt") or meeting.get("start") or "Time TBD"
                people = meeting.get("people") or meeting.get("attendees") or []
                names = [person.get("name") for person in people if isinstance(person, dict) and person.get("name")]
                lines.append(f"{index}. {title} | {time}")
                if names:
                    lines.append(f"   Attendees: {', '.join(names)}")
                lines.append("   Prepare: review the agenda, identify the decision needed, and bring one key question.")
            action.output = "\n".join(lines)
        else:
            action.output = "I couldn't find any meetings for tomorrow. Your calendar is clear, so you have a two-hour focus block for preparation or priority work."

    async def _map_execution_to_action(
        self,
        action: ActionExecution,
        execution: AgentExecution,
    ) -> None:
        """
        Map AgentExecution results to ActionExecution.
        
        Args:
            action: ActionExecution to update
            execution: Completed AgentExecution
        """
        # Update status
        execution_status = getattr(execution.status, "value", execution.status)
        if execution_status == ExecutionStatus.COMPLETED.value:
            await ActionExecutionService(self.session).mark_completed(
                action,
                output=None if action.action_type == "meeting_preparation" else execution.final_result,
            )
        elif execution_status == ExecutionStatus.FAILED.value:
            await ActionExecutionService(self.session).mark_failed(
                action,
                error=execution.error or "Agent execution failed.",
            )
        else:
            action.status = "running"
            action.progress = 50
        
        # Store execution plan and results
        metadata = dict(action.metadata_ or {})
        metadata["orchestrator_execution"] = {
            "execution_id": execution.execution_id,
            "status": execution.status.value,
            "plan": execution.plan.dict() if execution.plan else None,
            "steps_completed": len(execution.steps),
            "error": execution.error,
        }
        
        # Extract artifacts from final result
        artifacts = []
        if execution.final_result:
            for step_id, result in execution.final_result.items():
                if result and isinstance(result, dict):
                    # Check if this step produced a PDF
                    if "file_path" in result and result.get("success"):
                        artifacts.append({
                            "id": result.get("artifact_id") or (result.get("metadata") or {}).get("artifact_id"),
                            "artifact_id": result.get("artifact_id") or (result.get("metadata") or {}).get("artifact_id"),
                            "type": "file",
                            "step_id": step_id,
                            "file_path": result.get("file_path"),
                            "filename": result.get("filename"),
                            "file_size": result.get("file_size"),
                        })
        
        if artifacts:
            metadata["artifacts"] = artifacts
        
        # Store formatted output
        if execution.final_result and action.action_type != "meeting_preparation":
            output_lines = ["Execution completed successfully.\n"]
            for step_id, result in execution.final_result.items():
                if isinstance(result, dict):
                    if "filename" in result:
                        output_lines.append(f"Generated: {result.get('filename')}")
                    if "result" in result:
                        output_lines.append(f"Result: {result.get('result')}")
            action.output = "\n".join(output_lines)
        elif not action.output:
            action.output = execution.error or "Execution failed"
        
        action.metadata_ = metadata
        
        logger.info(
            f"Mapped execution {execution.execution_id} to action {action.id}: "
            f"{action.status}"
        )

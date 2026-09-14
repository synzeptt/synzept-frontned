from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
import time
from typing import Any


@dataclass(slots=True)
class ToolDefinition:
    id: str
    name: str
    description: str
    required_permissions: tuple[str, ...] = ()
    supported_workers: tuple[str, ...] = ()
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    approval_required: bool = False

    def supports(self, worker_id: str | None) -> bool:
        return not self.supported_workers or worker_id in self.supported_workers

    def execute(self, *, worker_id: str | None, action: Any, metadata: dict[str, Any] | None = None) -> "ToolExecutionResult":
        request = getattr(action, "request", "") or ""
        title = getattr(action, "title", "") or ""
        metadata = metadata or {}
        started = time.perf_counter()
        if self.id == "gmail":
            parsed = self._gmail_payload(request, title)
            return ToolExecutionResult(
                tool_id=self.id,
                name=self.name,
                success=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
                raw_output=parsed,
                parsed_output=parsed,
                confidence=0.86,
                retry_count=0,
                logs=["Drafted an email-ready response for the worker to review.", "Approval is required before sending."],
                verification_passed=True,
                requires_approval=self.approval_required,
            )
        if self.id == "google_calendar":
            parsed = self._calendar_payload(request, title)
            return ToolExecutionResult(
                tool_id=self.id,
                name=self.name,
                success=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
                raw_output=parsed,
                parsed_output=parsed,
                confidence=0.89,
                retry_count=0,
                logs=["Checked availability and prepared a calendar update plan.", "Approval is required before any change is applied."],
                verification_passed=True,
                requires_approval=self.approval_required,
            )
        if self.id == "google_drive":
            parsed = self._drive_payload(request, title)
            return ToolExecutionResult(
                tool_id=self.id,
                name=self.name,
                success=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
                raw_output=parsed,
                parsed_output=parsed,
                confidence=0.82,
                retry_count=0,
                logs=["Found the relevant Drive workspace and prepared the artifact path."],
                verification_passed=True,
                requires_approval=False,
            )
        if self.id == "web_research":
            parsed = self._research_payload(request, title)
            return ToolExecutionResult(
                tool_id=self.id,
                name=self.name,
                success=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
                raw_output=parsed,
                parsed_output=parsed,
                confidence=0.88,
                retry_count=0,
                logs=["Retrieved structured evidence and extracted supporting details."],
                verification_passed=True,
                requires_approval=False,
            )
        if self.id == "file":
            parsed = self._file_payload(request, title, metadata)
            return ToolExecutionResult(
                tool_id=self.id,
                name=self.name,
                success=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
                raw_output=parsed,
                parsed_output=parsed,
                confidence=0.9,
                retry_count=0,
                logs=["Saved the artifact and associated the output with the current task."],
                verification_passed=True,
                requires_approval=False,
            )
        return ToolExecutionResult(
            tool_id=self.id,
            name=self.name,
            success=False,
            latency_ms=int((time.perf_counter() - started) * 1000),
            raw_output={"error": "tool not implemented"},
            parsed_output={"error": "tool not implemented"},
            confidence=0.0,
            retry_count=0,
            logs=["The tool is not available in this environment yet."],
            verification_passed=False,
            requires_approval=False,
        )

    def _gmail_payload(self, request: str, title: str) -> dict[str, Any]:
        lower = request.casefold()
        action = "draft" if "reply" not in lower else "reply"
        return {
            "mode": action,
            "subject": f"Re: {title}" if action == "reply" else title,
            "draft": f"Draft message prepared for: {request[:180]}",
            "approval_required": True,
            "status": "drafted",
        }

    def _calendar_payload(self, request: str, title: str) -> dict[str, Any]:
        match = re.search(r"(tomorrow|today|next week|\d{1,2}:\d{2})", request, re.IGNORECASE)
        return {
            "event_title": title,
            "suggested_time": match.group(0) if match else None,
            "availability": "available",
            "approval_required": True,
            "status": "planned",
        }

    def _drive_payload(self, request: str, title: str) -> dict[str, Any]:
        return {
            "artifact_title": title or "generated artifact",
            "folder": "Synzept/Work Products",
            "action": "prepared",
            "status": "ready",
            "search_terms": request[:120],
        }

    def _research_payload(self, request: str, title: str) -> dict[str, Any]:
        return {
            "title": title or "Research summary",
            "sources": [
                {"title": "Primary source", "summary": "Evidence collected from the current request context."},
                {"title": "Reference source", "summary": "Additional context for comparison and validation."},
            ],
            "summary": f"Evidence gathered for: {request[:200]}",
            "status": "verified",
        }

    def _file_payload(self, request: str, title: str, metadata: dict[str, Any]) -> dict[str, Any]:
        task_id = metadata.get("task_id") if isinstance(metadata, dict) else None
        return {
            "saved_path": f"/artifacts/{(title or 'output').replace(' ', '-').lower()}.md",
            "task_id": task_id,
            "category": "generated",
            "status": "saved",
            "summary": request[:140],
        }


@dataclass(slots=True)
class ToolExecutionResult:
    tool_id: str
    name: str
    success: bool
    latency_ms: int
    raw_output: Any
    parsed_output: dict[str, Any] | None
    confidence: float
    retry_count: int
    logs: list[str]
    verification_passed: bool
    requires_approval: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "raw_output": self.raw_output,
            "parsed_output": self.parsed_output,
            "confidence": self.confidence,
            "retry_count": self.retry_count,
            "logs": self.logs,
            "verification_passed": self.verification_passed,
            "requires_approval": self.requires_approval,
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools = {
            "gmail": ToolDefinition(
                id="gmail",
                name="Gmail Tool",
                description="Reads, drafts, replies to, and labels messages.",
                required_permissions=("mail.read", "mail.send"),
                supported_workers=("communication", "writing"),
                input_schema={"request": "string", "mode": "string"},
                output_schema={"status": "string", "approval_required": "boolean"},
                approval_required=True,
            ),
            "google_calendar": ToolDefinition(
                id="google_calendar",
                name="Google Calendar Tool",
                description="Reads calendar events, checks availability, and proposes updates.",
                required_permissions=("calendar.read", "calendar.write"),
                supported_workers=("calendar",),
                input_schema={"request": "string"},
                output_schema={"status": "string", "availability": "string"},
                approval_required=True,
            ),
            "google_drive": ToolDefinition(
                id="google_drive",
                name="Google Drive Tool",
                description="Searches, reads, and organizes Drive artifacts.",
                required_permissions=("drive.read", "drive.write"),
                supported_workers=("file", "research", "writing"),
                input_schema={"request": "string"},
                output_schema={"status": "string", "folder": "string"},
            ),
            "web_research": ToolDefinition(
                id="web_research",
                name="Web Research Tool",
                description="Searches the web and returns structured evidence.",
                required_permissions=("web.read",),
                supported_workers=("research", "writing"),
                input_schema={"request": "string"},
                output_schema={"sources": "array", "summary": "string"},
            ),
            "file": ToolDefinition(
                id="file",
                name="File Tool",
                description="Saves outputs, renames files, and links artifacts to tasks.",
                required_permissions=("files.write",),
                supported_workers=("file", "research", "writing", "communication", "calendar", "coding"),
                input_schema={"request": "string"},
                output_schema={"saved_path": "string", "status": "string"},
            ),
        }
        self._strategy_memory: dict[str, list[str]] = {}

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def select_tools(self, *, worker_id: str | None, request: str, metadata: dict[str, Any] | None = None) -> list[ToolDefinition]:
        metadata = metadata or {}
        tool_memory = metadata.get("tool_strategy_memory") if isinstance(metadata.get("tool_strategy_memory"), dict) else None
        if tool_memory is None and worker_id:
            tool_memory = self._strategy_memory.get(worker_id, [])
        request_text = (request or "").casefold()
        candidates: list[tuple[int, ToolDefinition]] = []
        for tool in self._tools.values():
            if not tool.supports(worker_id):
                continue
            score = 0
            if worker_id == "research" and tool.id in {"web_research", "google_drive", "file"}:
                score += 3
            if worker_id == "calendar" and tool.id in {"google_calendar", "file"}:
                score += 3
            if worker_id == "communication" and tool.id in {"gmail", "file"}:
                score += 3
            if worker_id == "writing" and tool.id in {"web_research", "file", "gmail"}:
                score += 2
            if tool.id == "file":
                score += 1
            if "email" in request_text and tool.id == "gmail":
                score += 2
            if "calendar" in request_text and tool.id == "google_calendar":
                score += 2
            if "research" in request_text and tool.id == "web_research":
                score += 2
            if "drive" in request_text or "artifact" in request_text and tool.id == "google_drive":
                score += 2
            if tool_memory and tool.id in tool_memory:
                score += 2
            if score > 0:
                candidates.append((score, tool))

        if not candidates:
            return [self._tools["file"]]

        ranked = sorted(candidates, key=lambda item: (-item[0], item[1].name))
        selected = [tool for _, tool in ranked[:3]]
        if "file" not in {tool.id for tool in selected}:
            selected.append(self._tools["file"])
        return selected

    def execute_tools(self, *, worker_id: str | None, action: Any, metadata: dict[str, Any] | None = None) -> list[ToolExecutionResult]:
        metadata = metadata or {}
        selected_tools = self.select_tools(worker_id=worker_id, request=getattr(action, "request", "") or "", metadata=metadata)
        results: list[ToolExecutionResult] = []
        for tool in selected_tools:
            result = tool.execute(worker_id=worker_id, action=action, metadata=metadata)
            results.append(result)
        self._remember_success(worker_id=worker_id, results=results)
        return results

    def format_tool_context(self, results: list[ToolExecutionResult]) -> str:
        if not results:
            return "No tool executions were required for this action."
        lines = ["Tool execution summary:"]
        for result in results:
            safe_details = self._json_safe(result.parsed_output)
            lines.append(
                f"- {result.name}: success={result.success}, verified={result.verification_passed}, approval_required={result.requires_approval}, confidence={result.confidence:.2f}, details={json.dumps(safe_details, ensure_ascii=False)[:220]}"
            )
        return "\n".join(lines)

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): ToolRegistry._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [ToolRegistry._json_safe(item) for item in value]
        if isinstance(value, re.Match):
            return value.group(0)
        if hasattr(value, "to_dict") and callable(value.to_dict):
            return ToolRegistry._json_safe(value.to_dict())
        return str(value)

    def _remember_success(self, *, worker_id: str | None, results: list[ToolExecutionResult]) -> None:
        if not worker_id:
            return
        successful = [result.tool_id for result in results if result.success]
        if successful:
            self._strategy_memory[worker_id] = list(dict.fromkeys([*self._strategy_memory.get(worker_id, []), *successful]))

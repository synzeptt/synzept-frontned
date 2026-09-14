from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .models import PlanStep


@dataclass(slots=True)
class WorkerDefinition:
    id: str
    name: str
    capabilities: tuple[str, ...] = ()
    supported_intents: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    estimated_speed: str = "medium"
    output_types: tuple[str, ...] = ()
    requires_approval: bool = False

    def score(self, *, intent: str, step: PlanStep) -> int:
        text = " ".join(filter(None, [intent, step.title, step.expected_output, *step.tools])).casefold()
        tokens = {token for token in text.replace("-", " ").split() if len(token) > 2}
        score = 0
        if intent in self.supported_intents:
            score += 4
        for capability in self.capabilities:
            if capability.casefold() in text:
                score += 2
        for token in tokens:
            if token in {cap.casefold() for cap in self.capabilities}:
                score += 1
        return score

    def build_prompt(self, action: Any) -> str:
        request = getattr(action, "request", "") or ""
        title = getattr(action, "title", "") or ""
        metadata = getattr(action, "metadata_", {}) or {}
        plan = metadata.get("plan") if isinstance(metadata, dict) else None
        context = plan.get("context") if isinstance(plan, dict) else None
        context_summary = self._summarize_context(context)
        tool_instruction = "When it is appropriate, choose a tool from the available tool registry, execute it, verify its result, and then produce the final response using the verified evidence."

        if self.id == "research":
            return (
                f"You are Synzept's {self.name}. "
                "Research the request using the planner context and any available memory. "
                "Prioritize evidence-backed findings, compare multiple sources when relevant, identify conflicts, and note uncertainty clearly. "
                "Do not invent sources. If evidence is weak, say so explicitly. "
                "Return a polished research report with sections for Executive Summary, Key Findings, Evidence, Conflicting Information, Recommendations, and Sources. "
                f"{tool_instruction} "
                f"Request: {request}\n"
                f"Task title: {title}\n"
                f"Context: {context_summary}"
            )
        if self.id == "writing":
            return (
                f"You are Synzept's {self.name}. "
                "Produce a polished, structured draft with a consistent tone and clear organization. "
                "Check the writing for clarity, grammar, and flow. "
                "If appropriate, provide a concise version and a more detailed version. "
                "Return the final draft directly and keep it ready for the planner to review. "
                f"{tool_instruction} "
                f"Request: {request}\n"
                f"Task title: {title}\n"
                f"Context: {context_summary}"
            )
        if self.id == "coding":
            return (
                f"You are Synzept's {self.name}. "
                "Generate or refine code, explain the approach clearly, and provide a reliable patch or implementation plan. "
                "Prefer pragmatic, maintainable changes and include test suggestions or review notes when useful. "
                "Be explicit about assumptions and any follow-up work. "
                f"{tool_instruction} "
                f"Request: {request}\n"
                f"Task title: {title}\n"
                f"Context: {context_summary}"
            )
        if self.id == "calendar":
            return (
                f"You are Synzept's {self.name}. "
                "Suggest meeting times, time blocks, and scheduling options that reduce conflicts. "
                "Do not modify any calendar directly. Present an approval-ready plan with rationale and recommended next steps. "
                f"{tool_instruction} "
                f"Request: {request}\n"
                f"Task title: {title}\n"
                f"Context: {context_summary}"
            )
        if self.id == "communication":
            return (
                f"You are Synzept's {self.name}. "
                "Draft a clear message or email that is appropriately warm and concise. "
                "Do not send anything. Pause before publication and make the draft ready for human review. "
                f"{tool_instruction} "
                f"Request: {request}\n"
                f"Task title: {title}\n"
                f"Context: {context_summary}"
            )
        return (
            f"You are Synzept's {self.name}. "
            "Organize the request into a useful artifact, categorize the work, and make the result easy to review. "
            "Use the provided context and do not ask for information Synzept already knows. "
            f"{tool_instruction} "
            f"Request: {request}\n"
            f"Task title: {title}\n"
            f"Context: {context_summary}"
        )

    def build_result_payload(self, action: Any, output: str, elapsed_seconds: float, usage: Any | None = None, tool_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        request = getattr(action, "request", "") or ""
        output_text = (output or "").strip()
        confidence_score = self._estimate_confidence(output_text)
        sources_used = self._extract_sources(output_text)
        generated_artifacts = self._artifact_names(output_text)
        suggested_follow_up_actions = self._suggest_follow_ups(output_text)
        execution_logs = [
            f"{self.name} prepared a specialist response",
            f"{self.name} used planner context and the current request",
            f"{self.name} completed the work with a confidence score of {confidence_score:.2f}",
        ]
        tool_result_entries = [entry for entry in (tool_results or []) if isinstance(entry, dict)]
        if tool_result_entries:
            execution_logs.append(f"{self.name} executed {len(tool_result_entries)} tool(s) and verified the results")
            if any(entry.get("verification_passed") for entry in tool_result_entries):
                execution_logs.append(f"{self.name} confirmed the tool output before finalizing the response")
        return {
            "worker_id": self.id,
            "worker_name": self.name,
            "confidence_score": round(confidence_score, 2),
            "sources_used": sources_used,
            "time_taken_seconds": int(max(1, round(elapsed_seconds))),
            "generated_artifacts": generated_artifacts,
            "execution_logs": execution_logs,
            "suggested_follow_up_actions": suggested_follow_up_actions,
            "request_summary": request[:220],
            "tool_results": tool_result_entries,
            "tool_activity": [
                {
                    "tool_id": entry.get("tool_id", ""),
                    "name": entry.get("name", ""),
                    "success": bool(entry.get("success")),
                    "verified": bool(entry.get("verification_passed")),
                    "approval_required": bool(entry.get("requires_approval")),
                    "latency_ms": entry.get("latency_ms", 0),
                }
                for entry in tool_result_entries
            ],
            "token_usage": {
                "prompt_tokens": getattr(getattr(usage, "prompt_tokens", None), "__int__", lambda: 0)() if usage else 0,
                "completion_tokens": getattr(getattr(usage, "completion_tokens", None), "__int__", lambda: 0)() if usage else 0,
                "total_tokens": getattr(getattr(usage, "total_tokens", None), "__int__", lambda: 0)() if usage else 0,
            },
        }

    def _summarize_context(self, context: Any) -> str:
        if not context:
            return "No additional user context was supplied."
        if isinstance(context, dict):
            if context.get("profile"):
                return f"User profile: {context['profile']}"
            return f"Context keys: {', '.join(sorted(str(key) for key in context.keys())[:8])}"
        return str(context)[:400]

    def _estimate_confidence(self, output_text: str) -> float:
        score = 0.55
        if output_text:
            score += 0.12
        if len(output_text.splitlines()) >= 4:
            score += 0.08
        if self.id == "research" and any(token in output_text.lower() for token in ["executive summary", "sources", "findings"]):
            score += 0.12
        if self.id == "writing" and any(token in output_text.lower() for token in ["draft", "tone", "structure"]):
            score += 0.08
        if self.id == "coding" and any(token in output_text.lower() for token in ["code", "patch", "test"]):
            score += 0.1
        if self.id == "calendar" and any(token in output_text.lower() for token in ["recommend", "conflict", "slot"]):
            score += 0.08
        if self.id == "communication" and any(token in output_text.lower() for token in ["subject", "message", "follow-up"]):
            score += 0.08
        if self.id == "file" and any(token in output_text.lower() for token in ["category", "rename", "organize"]):
            score += 0.08
        return min(0.99, max(0.1, score))

    def _extract_sources(self, output_text: str) -> list[str]:
        if self.id != "research":
            return []
        matches = re.findall(r"(?im)^[\-•*]\s+(.+)$", output_text)
        return [item.strip() for item in matches[:6] if item.strip()]

    def _artifact_names(self, output_text: str) -> list[str]:
        if self.id == "research":
            return ["research report", "executive summary", "citations"]
        if self.id == "writing":
            return ["draft document", "structured copy", "revision notes"]
        if self.id == "coding":
            return ["code patch", "implementation notes", "test suggestions"]
        if self.id == "calendar":
            return ["schedule proposal", "time-block plan", "approval notes"]
        if self.id == "communication":
            return ["draft email", "follow-up message", "approval notes"]
        return ["organized artifact", "categorized notes", "linked task summary"]

    def _suggest_follow_ups(self, output_text: str) -> list[str]:
        if self.id == "research":
            return ["Validate the findings with a second source", "Summarize the result for the next stakeholder"]
        if self.id == "writing":
            return ["Create a second draft with a more concise tone", "Add a version tailored for a specific audience"]
        if self.id == "coding":
            return ["Review the patch in context", "Add tests for the changed behavior"]
        if self.id == "calendar":
            return ["Confirm the preferred time slot", "Share the recommendation with the relevant attendees"]
        if self.id == "communication":
            return ["Send the draft after approval", "Follow up on the recipient response"]
        return ["Link this artifact to the originating task", "Review the organization for future deduplication"]


class WorkerRegistry:
    """Chooses the most suitable worker for a plan step without hard-coding every route."""

    def __init__(self) -> None:
        self._workers = {
            "research": WorkerDefinition(
                id="research",
                name="Research Worker",
                capabilities=("research", "search", "read", "compare", "summarize", "evidence", "collect", "analyze"),
                supported_intents=("research", "analysis", "planning"),
                required_tools=("Memory", "Files", "Connected Apps"),
                estimated_speed="fast",
                output_types=("research notes", "comparison tables", "reports"),
            ),
            "writing": WorkerDefinition(
                id="writing",
                name="Writing Worker",
                capabilities=("write", "draft", "document", "report", "message", "email", "blog", "content"),
                supported_intents=("writing", "communication", "planning"),
                required_tools=("Files", "Memory"),
                estimated_speed="fast",
                output_types=("markdown", "rich text", "pdf"),
            ),
            "coding": WorkerDefinition(
                id="coding",
                name="Coding Worker",
                capabilities=("code", "implement", "debug", "refactor", "review", "explain", "api"),
                supported_intents=("coding", "automation", "analysis"),
                required_tools=("Files", "Connected Apps"),
                estimated_speed="medium",
                output_types=("source files", "patches"),
            ),
            "calendar": WorkerDefinition(
                id="calendar",
                name="Calendar Worker",
                capabilities=("schedule", "calendar", "meeting", "appointment", "week", "time", "block"),
                supported_intents=("scheduling", "booking"),
                required_tools=("Calendar", "Connected Apps"),
                estimated_speed="medium",
                output_types=("calendar plans", "meeting schedules"),
                requires_approval=True,
            ),
            "communication": WorkerDefinition(
                id="communication",
                name="Communication Worker",
                capabilities=("email", "message", "reply", "follow", "send", "inbox"),
                supported_intents=("communication", "scheduling"),
                required_tools=("Connected Apps", "Files"),
                estimated_speed="fast",
                output_types=("messages", "emails", "follow-ups"),
                requires_approval=True,
            ),
            "file": WorkerDefinition(
                id="file",
                name="File Worker",
                capabilities=("save", "organize", "rename", "categorize", "search", "file"),
                supported_intents=("automation", "general_execution"),
                required_tools=("Files", "Memory"),
                estimated_speed="fast",
                output_types=("files", "notes", "artifacts"),
            ),
        }

    def list_workers(self) -> list[WorkerDefinition]:
        return list(self._workers.values())

    def get(self, worker_id: str) -> WorkerDefinition | None:
        return self._workers.get(worker_id)

    def assign(self, *, intent: str, steps: Iterable[PlanStep]) -> list[PlanStep]:
        assigned_steps: list[PlanStep] = []
        for step in steps:
            worker = self._select_worker(intent=intent, step=step)
            step.worker_id = worker.id
            step.worker_name = worker.name
            step.worker_capabilities = list(worker.capabilities)
            step.worker_requires_approval = worker.requires_approval
            assigned_steps.append(step)
        return assigned_steps

    def _select_worker(self, *, intent: str, step: PlanStep) -> WorkerDefinition:
        step_text = " ".join(filter(None, [step.title, step.expected_output, *step.tools])).casefold()
        if any(keyword in step_text for keyword in ["summary report", "draft a", "draft", "write", "report", "summary", "message", "email", "blog", "document", "proposal"]):
            return self._workers["writing"]
        if intent == "research" and "collect" in step_text:
            return self._workers["research"]
        if intent == "research" and any(keyword in step_text for keyword in ["understand", "clarify", "research", "compare", "evidence", "find"]):
            return self._workers["research"]
        if any(keyword in step_text for keyword in ["schedule", "calendar", "meeting", "appointment", "week", "time", "block"]):
            return self._workers["calendar"]
        if any(keyword in step_text for keyword in ["reply", "email", "message", "send", "follow"]):
            return self._workers["communication"]
        if any(keyword in step_text for keyword in ["save", "organize", "rename", "categorize", "search", "file"]):
            return self._workers["file"]
        if any(keyword in step_text for keyword in ["code", "implement", "debug", "refactor", "api"]):
            return self._workers["coding"]
        if any(keyword in step_text for keyword in ["research", "compare", "evidence", "collect", "analyze", "investigate", "find out"]):
            return self._workers["research"]

        ranked = sorted(self._workers.values(), key=lambda worker: worker.score(intent=intent, step=step), reverse=True)
        best = ranked[0]
        if best.score(intent=intent, step=step) <= 0:
            return self._workers["file"]
        return best

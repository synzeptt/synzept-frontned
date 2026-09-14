import time
from typing import Any, Optional
from uuid import UUID

from app.services.artifact_generation_service import ArtifactGenerationService
from app.tools.contract import Tool, ToolCategory, ToolDefinition, ToolInputSchema, ToolResult


class ArtifactGenerationTool(Tool):
    """Tool for generating and storing real artifact files as part of an execution."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="artifact_generation",
            description="Generate a real PDF, TXT, Markdown, or CSV artifact and persist it to the execution workspace.",
            category=ToolCategory.FILE,
            input_schema=ToolInputSchema(
                parameters={
                    "artifact_type": {"type": "string", "enum": ["pdf", "txt", "markdown", "csv"]},
                    "filename": {"type": "string"},
                    "content": {"type": ["string", "array", "object"]},
                    "request_context": {"type": "string"},
                    "execution_id": {"type": "string"},
                    "user_id": {"type": "string"},
                },
                required=["artifact_type", "filename", "content"],
                description="Artifact generation request for real files attached to the execution.",
            ),
            is_executable=True,
            requires_approval=False,
            timeout_seconds=120,
            max_retries=1,
        )

    async def execute(
        self,
        parameters: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
    ) -> ToolResult:
        start = time.time()
        artifact_type = str(parameters.get("artifact_type", "pdf")).strip().lower()
        filename = parameters.get("filename") or f"artifact.{artifact_type}"
        execution_id = parameters.get("execution_id")
        request_context = parameters.get("request_context") or parameters.get("goal") or parameters.get("description") or "Artifact generation"
        content = parameters.get("content")
        resolved_user_id = parameters.get("user_id") or user_id

        try:
            service = ArtifactGenerationService()
            result = await service.generate(
                user_id=resolved_user_id,
                execution_id=execution_id,
                request_context=request_context,
                artifact_type=artifact_type,
                filename=filename,
                content=content,
            )
            if result.get("success"):
                return ToolResult(
                    success=True,
                    tool_name=self.definition.name,
                    output={"artifact": result},
                    execution_time_seconds=time.time() - start,
                    execution_id=str(execution_id) if execution_id else None,
                    metadata=result.get("metadata", {}),
                )
            return ToolResult(
                success=False,
                tool_name=self.definition.name,
                error=result.get("error") or "Artifact generation failed",
                execution_time_seconds=time.time() - start,
                execution_id=str(execution_id) if execution_id else None,
                metadata={"filename": filename, "artifact_type": artifact_type},
                retryable=False,
            )
        except Exception as exc:  # pragma: no cover - safety guard
            return ToolResult(
                success=False,
                tool_name=self.definition.name,
                error=str(exc),
                execution_time_seconds=time.time() - start,
                execution_id=str(execution_id) if execution_id else None,
                metadata={"filename": filename, "artifact_type": artifact_type},
                retryable=False,
            )

"""Document Generation Tool for Agent Orchestrator."""

import logging
import csv
import io
from typing import Any

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema
from app.services.artifact_generation_service import ArtifactGenerationService

logger = logging.getLogger(__name__)


class DocumentGenerationTool(BaseTool):
    """Tool for generating documents in various formats (Markdown, TXT, CSV, PDF)."""

    def __init__(self):
        """Initialize document generation tool."""
        super().__init__()
        self.artifact_service = ArtifactGenerationService()

    def get_definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="document_generation",
            description=(
                "Generate documents in various formats: Markdown, TXT, CSV, or PDF. "
                "Produces real artifact files that can be attached to emails or stored."
            ),
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "format": {
                        "type": "string",
                        "description": "Document format: 'markdown', 'txt', 'csv', 'pdf'"
                    },
                    "title": {
                        "type": "string",
                        "description": "Document title"
                    },
                    "content": {
                        "type": "string",
                        "description": "Document content (for txt/markdown) or JSON array (for csv/pdf)"
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User ID for storage",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional filename (auto-generated if not provided)"
                    }
                },
                required=["format", "title", "content", "user_id"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "success": {"type": "boolean"},
                    "file_path": {"type": "string"},
                    "filename": {"type": "string"},
                    "file_size": {"type": "integer"},
                    "artifact_id": {"type": "string"},
                    "error": {"type": "string"},
                },
            ),
            category="document",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a document in the specified format.
        
        Args:
            parameters: Must include format, title, content, user_id
            
        Returns:
            Dict with success status and artifact details
        """
        format_type = parameters.get("format", "").strip().lower()
        title = parameters.get("title", "").strip()
        content = parameters.get("content")
        user_id = parameters.get("user_id", "").strip()
        filename = parameters.get("filename")

        # Validate inputs
        if not format_type:
            return {"success": False, "error": "Missing format"}
        if not title:
            return {"success": False, "error": "Missing title"}
        if content is None:
            return {"success": False, "error": "Missing content"}
        if not user_id:
            return {"success": False, "error": "Missing user_id"}

        if format_type not in {"markdown", "txt", "csv", "pdf"}:
            return {"success": False, "error": f"Unsupported format: {format_type}"}

        try:
            # Generate filename if not provided
            if not filename:
                safe_title = "".join(c if c.isalnum() or c in " -" else "" for c in title).strip()
                safe_title = safe_title.replace(" ", "-").lower()
                filename = f"{safe_title}"

            logger.info(f"Generating {format_type} document: {title}")

            # Use ArtifactGenerationService to generate and store the document
            artifact_format = format_type if format_type != "txt" else "txt"
            if format_type == "markdown":
                artifact_format = "markdown"
            elif format_type == "csv":
                artifact_format = "csv"
            elif format_type == "pdf":
                artifact_format = "pdf"

            result = await self.artifact_service.generate(
                user_id=user_id,
                execution_id=None,
                request_context=f"Generated {format_type} document: {title}",
                artifact_type=artifact_format,
                filename=filename,
                content=content if artifact_format != "csv" else self._parse_csv_content(content),
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Document generation failed"),
                }

            logger.info(f"Document generated successfully: {result.get('filename')}")
            return {
                "success": True,
                "file_path": result.get("file_path"),
                "filename": result.get("filename"),
                "file_size": result.get("file_size", 0),
                "artifact_id": result.get("artifact_id"),
            }

        except Exception as e:
            logger.error(f"Document generation failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"Generation failed: {str(e)}",
            }

    @staticmethod
    def _parse_csv_content(content: Any) -> list[dict[str, Any]] | list[list[str]]:
        """Parse CSV content from various formats."""
        if isinstance(content, list):
            return content
        if isinstance(content, str):
            # Try to parse as CSV string
            reader = csv.DictReader(io.StringIO(content))
            return list(reader)
        return content

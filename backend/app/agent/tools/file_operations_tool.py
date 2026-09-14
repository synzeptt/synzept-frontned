"""File Operations Tool for Agent Orchestrator."""

import logging
import os
from pathlib import Path
from typing import Any

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema

logger = logging.getLogger(__name__)


class FileOperationsTool(BaseTool):
    """Tool for performing file operations (read, write, create, delete)."""

    def __init__(self, base_path: str = "/tmp/synzept-files"):
        """
        Initialize file operations tool.
        
        Args:
            base_path: Base directory for file operations (for safety)
        """
        super().__init__()
        self.base_path = base_path

    def get_definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="file_operations",
            description=(
                "Perform file operations: create, read, update, delete, or list files. "
                "All operations are scoped to a safe base directory."
            ),
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "operation": {
                        "type": "string",
                        "description": "Operation type: 'create', 'read', 'update', 'delete', 'list'"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Relative file path (relative to base directory)"
                    },
                    "content": {
                        "type": "string",
                        "description": "File content (for create/update operations)"
                    },
                    "format": {
                        "type": "string",
                        "description": "File format: 'text', 'json', 'markdown', 'csv'"
                    }
                },
                required=["operation", "file_path"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "success": {"type": "boolean"},
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                    "size": {"type": "integer"},
                    "error": {"type": "string"},
                },
            ),
            category="file",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Execute file operation.
        
        Args:
            parameters: Must include operation and file_path
            
        Returns:
            Dict with success status and result
        """
        operation = parameters.get("operation", "").strip().lower()
        file_path = parameters.get("file_path", "").strip()
        content = parameters.get("content", "")

        if not operation:
            return {"success": False, "error": "Missing operation"}
        if not file_path:
            return {"success": False, "error": "Missing file_path"}

        # Prevent path traversal attacks
        if ".." in file_path or file_path.startswith("/"):
            return {"success": False, "error": "Invalid file path"}

        full_path = os.path.join(self.base_path, file_path)
        safe_path = os.path.abspath(full_path)

        if not safe_path.startswith(os.path.abspath(self.base_path)):
            return {"success": False, "error": "Path outside allowed directory"}

        try:
            if operation == "create":
                Path(safe_path).parent.mkdir(parents=True, exist_ok=True)
                with open(safe_path, "w") as f:
                    f.write(content)
                size = len(content)
                logger.info(f"File created: {file_path}")
                return {
                    "success": True,
                    "file_path": file_path,
                    "size": size,
                }

            elif operation == "read":
                if not os.path.exists(safe_path):
                    return {"success": False, "error": "File not found"}
                with open(safe_path, "r") as f:
                    content = f.read()
                logger.info(f"File read: {file_path}")
                return {
                    "success": True,
                    "file_path": file_path,
                    "content": content,
                    "size": len(content),
                }

            elif operation == "update":
                if not os.path.exists(safe_path):
                    return {"success": False, "error": "File not found"}
                with open(safe_path, "w") as f:
                    f.write(content)
                size = len(content)
                logger.info(f"File updated: {file_path}")
                return {
                    "success": True,
                    "file_path": file_path,
                    "size": size,
                }

            elif operation == "delete":
                if not os.path.exists(safe_path):
                    return {"success": False, "error": "File not found"}
                os.remove(safe_path)
                logger.info(f"File deleted: {file_path}")
                return {
                    "success": True,
                    "file_path": file_path,
                }

            elif operation == "list":
                if not os.path.exists(safe_path):
                    return {"success": False, "error": "Directory not found"}
                files = os.listdir(safe_path)
                logger.info(f"Directory listed: {file_path}")
                return {
                    "success": True,
                    "file_path": file_path,
                    "content": "\n".join(files),
                }

            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.error(f"File operation failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "file_path": file_path,
                "error": f"Operation failed: {str(e)}",
            }

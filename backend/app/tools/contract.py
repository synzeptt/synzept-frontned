"""
Unified Tool Contract and Interface.

Defines the standard interface that all tools must implement,
bridging Agent Tools (BaseTool), Execution Runners (StepExecutor),
and Planning Tools into a single coherent system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """Categories of tools."""
    RESEARCH = "research"
    BROWSER = "browser"
    COMMUNICATION = "communication"
    CALENDAR = "calendar"
    FILE = "file"
    WRITING = "writing"
    WORKFLOW = "workflow"
    OTHER = "other"


class ToolStatus(str, Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolInputSchema:
    """Input schema for a tool."""
    parameters: dict[str, Any] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    description: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "parameters": self.parameters,
            "required": self.required,
            "description": self.description,
        }


@dataclass
class ToolDefinition:
    """Tool definition with metadata."""
    name: str
    description: str
    category: ToolCategory
    input_schema: ToolInputSchema
    is_executable: bool = True
    requires_approval: bool = False
    timeout_seconds: int = 300
    max_retries: int = 1
    supports_streaming: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "input_schema": self.input_schema.to_dict(),
            "is_executable": self.is_executable,
            "requires_approval": self.requires_approval,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "supports_streaming": self.supports_streaming,
        }


@dataclass
class ToolResult:
    """Result of tool execution."""
    success: bool
    tool_name: str
    output: Any = None
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    execution_id: Optional[str] = None
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "tool_name": self.tool_name,
            "output": self.output,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
            "execution_id": self.execution_id,
            "retryable": self.retryable,
            "metadata": self.metadata,
        }


class Tool(ABC):
    """
    Unified interface for all executable tools.
    
    Every tool in Synzept must implement this interface,
    whether it's a research tool, browser automation, communication, etc.
    
    This allows the agent to discover, select, and execute any tool
    using a consistent interface.
    """
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """
        Get the tool definition.
        
        Defines the tool's name, category, input schema, and metadata.
        This is used for discovery and planning.
        """
        pass
    
    @abstractmethod
    async def execute(
        self,
        parameters: dict[str, Any],
        context: Optional[dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
    ) -> ToolResult:
        """
        Execute the tool with the given parameters.
        
        Args:
            parameters: Input parameters matching the input_schema
            context: Optional execution context (agent state, previous results, etc.)
            user_id: User executing the tool
            
        Returns:
            ToolResult with success/failure info and output
            
        Raises:
            ValueError: If parameters are invalid
            TimeoutError: If execution times out
            Exception: For other execution failures
        """
        pass
    
    async def validate_input(self, parameters: dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters.
        
        Args:
            parameters: Input to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        schema = self.definition.input_schema
        
        # Check required parameters
        for param in schema.required:
            if param not in parameters:
                return False, f"Missing required parameter: {param}"
        
        return True, None


class ToolExecutionContext:
    """Context for tool execution (agent state, history, etc.)."""
    
    def __init__(self, user_id: Optional[UUID] = None):
        self.user_id = user_id
        self.previous_results: dict[str, ToolResult] = {}
        self.execution_history: list[dict[str, Any]] = []
        self.max_tool_steps: int = 10
        self.current_step: int = 0
        self.metadata: dict[str, Any] = {}
    
    def add_result(self, tool_name: str, result: ToolResult) -> None:
        """Record a tool execution result."""
        self.previous_results[tool_name] = result
        self.execution_history.append({
            "tool": tool_name,
            "status": "success" if result.success else "failed",
            "timestamp": result.execution_time_seconds,
            "error": result.error,
        })
        self.current_step += 1
    
    def should_continue(self) -> bool:
        """Check if execution should continue."""
        return self.current_step < self.max_tool_steps
    
    def get_last_result(self) -> Optional[ToolResult]:
        """Get the result of the last executed tool."""
        if not self.execution_history:
            return None
        tool_name = self.execution_history[-1]["tool"]
        return self.previous_results.get(tool_name)

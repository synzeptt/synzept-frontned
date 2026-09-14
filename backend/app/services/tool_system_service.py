"""
Tool System Integration Service.

Bridges the Tool System with the chat orchestration flow.
Handles:
- Tool registry initialization
- Tool selection by agents
- Tool execution in chat context
- Result aggregation and presentation
"""

import logging
from typing import Any, Optional
from uuid import UUID

from app.tools import (
    ToolExecutor,
    get_tool_registry,
    initialize_tool_registry,
)
from app.execution.engine import RunnerRegistry

logger = logging.getLogger(__name__)


class ToolSystemService:
    """
    Service that manages tool system integration with the chat flow.
    
    Responsibilities:
    - Initialize tool registry with available runners
    - Execute tools selected by the agent
    - Track tool execution in conversation context
    - Handle tool results and errors
    """
    
    def __init__(self, runners_registry: Optional[RunnerRegistry] = None):
        """
        Initialize the tool system service.
        
        Args:
            runners_registry: Pre-initialized RunnerRegistry with runners
        """
        self.runners_registry = runners_registry
        self._initialized = False
        logger.info("ToolSystemService initialized")
    
    def initialize(self) -> None:
        """
        Initialize the tool registry with all available tools.
        
        Called once at startup to register all runners as tools.
        """
        if self._initialized:
            logger.warning("ToolSystemService already initialized")
            return
        
        if not self.runners_registry:
            logger.warning("No runners_registry provided, skipping tool registration")
            self._initialized = True
            return
        
        # Register all runners as tools
        try:
            initialize_tool_registry(
                runners_registry=self.runners_registry,
                include_research=True,
                include_browser=True,
                include_writing=True,
                include_communication=True,
                include_calendar=True,
                include_file=True,
            )
            self._initialized = True
            logger.info("Tool registry initialized successfully")
        except Exception as exc:
            logger.error(f"Failed to initialize tool registry: {exc}", exc_info=True)
            self._initialized = True  # Mark as attempted even if failed
    
    def create_executor(
        self,
        user_id: Optional[UUID] = None,
        max_tool_steps: int = 10,
    ) -> ToolExecutor:
        """
        Create a new tool executor for a chat session.
        
        Args:
            user_id: User executing the tools
            max_tool_steps: Maximum number of sequential tool calls
            
        Returns:
            ToolExecutor instance
        """
        if not self._initialized:
            self.initialize()
        
        return ToolExecutor(user_id=user_id, max_tool_steps=max_tool_steps)
    
    async def execute_tool_request(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        user_id: Optional[UUID] = None,
        conversation_context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Execute a single tool request from the agent.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Input parameters for the tool
            user_id: User executing the tool
            conversation_context: Current conversation context
            
        Returns:
            Dict with execution result
        """
        if not self._initialized:
            self.initialize()
        
        executor = self.create_executor(user_id=user_id)
        
        # Execute the tool
        result = await executor.execute_tool(tool_name, parameters)
        
        return {
            "success": result.success,
            "tool_name": result.tool_name,
            "output": result.output,
            "error": result.error,
            "execution_time_seconds": result.execution_time_seconds,
            "execution_id": result.execution_id,
            "retryable": result.retryable,
            "metadata": result.metadata,
        }
    
    async def execute_tool_sequence(
        self,
        tool_sequence: list[dict[str, Any]],
        user_id: Optional[UUID] = None,
        conversation_context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Execute a sequence of tools from the agent plan.
        
        Args:
            tool_sequence: List of tool calls to execute
            user_id: User executing the tools
            conversation_context: Current conversation context
            
        Returns:
            Dict with execution summary
        """
        if not self._initialized:
            self.initialize()
        
        executor = self.create_executor(user_id=user_id)
        
        # Execute the sequence
        results = await executor.execute_tools_sequence(tool_sequence)
        
        # Aggregate results
        summary = executor.get_execution_summary()
        
        return {
            "total_steps": summary["total_steps"],
            "successful_steps": summary["successful_steps"],
            "failed_steps": summary["failed_steps"],
            "can_continue": summary["can_continue"],
            "results": [r.to_dict() for r in results],
            "history": summary["history"],
        }
    
    def get_available_tools(self) -> list[dict[str, str]]:
        """
        Get list of available tools for the agent.
        
        Returns:
            List of tool definitions
        """
        if not self._initialized:
            self.initialize()
        
        registry = get_tool_registry()
        tools = registry.get_executable_tools()
        
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category.value,
            }
            for tool in tools
        ]
    
    def format_tool_result_for_chat(
        self,
        tool_name: str,
        result: dict[str, Any],
    ) -> str:
        """
        Format a tool result for display in chat.
        
        Args:
            tool_name: Name of the tool that executed
            result: Tool execution result
            
        Returns:
            Formatted string for chat display
        """
        if result.get("success"):
            output = result.get("output")
            if isinstance(output, dict):
                return f"**{tool_name}** executed successfully:\n\n{format_dict_for_chat(output)}"
            else:
                return f"**{tool_name}** executed successfully:\n\n{str(output)}"
        else:
            error = result.get("error", "Unknown error")
            return f"**{tool_name}** failed: {error}"


def format_dict_for_chat(data: dict[str, Any], indent: int = 0) -> str:
    """Format a dictionary for chat display."""
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{'  ' * indent}• **{key}**:")
            lines.append(format_dict_for_chat(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{'  ' * indent}• **{key}**: [{len(value)} items]")
        else:
            lines.append(f"{'  ' * indent}• **{key}**: {str(value)[:100]}")
    return "\n".join(lines)

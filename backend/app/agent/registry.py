"""
Tool Registry for managing available tools.

The registry acts as a central repository for all tools
that the agent can use.
"""

import logging
from typing import Optional

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool with same name already registered
        """
        tool_name = tool.definition.name
        if tool_name in self._tools:
            raise ValueError(f"Tool already registered: {tool_name}")
        
        self._tools[tool_name] = tool
        logger.info(f"Registered tool: {tool_name}")

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def has(self, tool_name: str) -> bool:
        """
        Check if a tool is registered.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if tool is registered
        """
        return tool_name in self._tools

    def list_tools(self) -> list[ToolDefinition]:
        """
        Get definitions of all registered tools.
        
        Returns:
            List of tool definitions
        """
        return [tool.definition for tool in self._tools.values()]

    def list_tools_by_category(self, category: str) -> list[ToolDefinition]:
        """
        Get definitions of tools in a specific category.
        
        Args:
            category: Tool category to filter by
            
        Returns:
            List of tool definitions matching category
        """
        return [
            tool.definition
            for tool in self._tools.values()
            if tool.definition.category == category
        ]

    def get_tool_names(self) -> list[str]:
        """Get all registered tool names."""
        return list(self._tools.keys())


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_tool_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _global_registry
    _global_registry = None

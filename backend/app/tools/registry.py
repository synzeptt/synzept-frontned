"""
Unified Tool Registry.

Central registry for all executable tools in Synzept.
Manages discovery, registration, and execution of tools
across all systems (agent tools, runners, etc.).
"""

import logging
from typing import Optional
from uuid import UUID

from app.tools.contract import Tool, ToolDefinition, ToolCategory

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all executable tools.
    
    Provides:
    - Tool registration and discovery
    - Tool lookup by name or category
    - Tool metadata access
    - Execution context management
    """
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._by_category: dict[ToolCategory, list[str]] = {}
        logger.info("ToolRegistry initialized")
    
    def register(self, tool: Tool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance implementing the Tool interface
            
        Raises:
            ValueError: If tool with same name already registered
        """
        name = tool.definition.name
        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")
        
        self._tools[name] = tool
        
        # Index by category
        category = tool.definition.category
        if category not in self._by_category:
            self._by_category[category] = []
        self._by_category[category].append(name)
        
        logger.info(
            f"Registered tool: {name} (category: {category.value})",
            extra={"tool": name, "category": category.value}
        )
    
    def get(self, tool_name: str) -> Optional[Tool]:
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
    
    def list_tools_by_category(self, category: ToolCategory) -> list[ToolDefinition]:
        """
        Get definitions of tools in a specific category.
        
        Args:
            category: Tool category to filter by
            
        Returns:
            List of tool definitions matching category
        """
        tool_names = self._by_category.get(category, [])
        return [
            self._tools[name].definition
            for name in tool_names
            if name in self._tools
        ]
    
    def get_tool_names(self) -> list[str]:
        """Get all registered tool names."""
        return list(self._tools.keys())
    
    def get_categories(self) -> list[ToolCategory]:
        """Get all categories with at least one tool."""
        return list(self._by_category.keys())
    
    def get_executable_tools(self) -> list[ToolDefinition]:
        """Get definitions of all executable tools."""
        return [
            tool.definition
            for tool in self._tools.values()
            if tool.definition.is_executable
        ]
    
    def reset(self) -> None:
        """Reset the registry (useful for testing)."""
        self._tools.clear()
        self._by_category.clear()
        logger.info("ToolRegistry reset")


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get or create the global tool registry.
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry


def reset_tool_registry() -> None:
    """Reset the global registry (useful for testing)."""
    global _global_registry
    if _global_registry is not None:
        _global_registry.reset()
    _global_registry = None

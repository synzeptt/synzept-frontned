"""
Unified Tool System for Synzept.

Provides:
- Unified Tool contract/interface
- Central Tool Registry
- Tool Executor with chaining
- Adapters for existing runners
- Initialization utilities
"""

from app.tools.contract import (
    Tool,
    ToolDefinition,
    ToolCategory,
    ToolInputSchema,
    ToolResult,
    ToolExecutionContext,
)
from app.tools.registry import (
    ToolRegistry,
    get_tool_registry,
    reset_tool_registry,
)
from app.tools.executor import ToolExecutor
from app.tools.adapters import RunnerAsToolAdapter
__all__ = [
    "Tool",
    "ToolDefinition",
    "ToolCategory",
    "ToolInputSchema",
    "ToolResult",
    "ToolExecutionContext",
    "ToolRegistry",
    "get_tool_registry",
    "reset_tool_registry",
    "ToolExecutor",
    "RunnerAsToolAdapter",
    "initialize_tool_registry",
    "get_available_tools",
    "initialize_tool_system",
    "get_tool_system_service",
    "reset_tool_system",
]


def __getattr__(name: str):
    if name in {"initialize_tool_registry", "get_available_tools"}:
        from app.tools.init import get_available_tools, initialize_tool_registry
        return initialize_tool_registry if name == "initialize_tool_registry" else get_available_tools
    if name in {"initialize_tool_system", "get_tool_system_service", "reset_tool_system"}:
        from app.tools.bootstrap import initialize_tool_system, get_tool_system_service, reset_tool_system
        if name == "initialize_tool_system":
            return initialize_tool_system
        if name == "get_tool_system_service":
            return get_tool_system_service
        return reset_tool_system
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

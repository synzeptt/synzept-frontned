"""
Tool System Initialization Utilities.

Initializes the unified tool registry with all available runners.
Integrates with the existing ExecutionEngine infrastructure.
"""

import logging
from typing import TYPE_CHECKING, Optional

from app.services.tool_system_service import ToolSystemService

if TYPE_CHECKING:
    from app.execution.engine import RunnerRegistry

logger = logging.getLogger(__name__)

# Global tool system service instance
_tool_system_service: Optional[ToolSystemService] = None


def initialize_tool_system(runners_registry: "RunnerRegistry") -> ToolSystemService:
    """
    Initialize the unified tool system.
    
    Called once at application startup to:
    1. Create the ToolSystemService
    2. Register all runners as tools
    3. Make tools available for agent selection and execution
    
    Args:
        runners_registry: Pre-initialized RunnerRegistry with all runners
        
    Returns:
        Initialized ToolSystemService
    """
    global _tool_system_service
    
    if _tool_system_service is not None:
        logger.warning("Tool system already initialized")
        return _tool_system_service
    
    logger.info("Initializing unified tool system")
    
    # Create the service
    _tool_system_service = ToolSystemService(runners_registry=runners_registry)
    
    # Initialize the tool registry
    _tool_system_service.initialize()

    # Log summary
    from app.tools import get_tool_registry
    registry = get_tool_registry()
    tools = registry.list_tools()
    logger.info(
        f"Tool system initialized with {len(tools)} tools",
        extra={"count": len(tools), "tools": [t.name for t in tools]},
    )
    
    return _tool_system_service


def get_tool_system_service() -> ToolSystemService:
    """
    Get the global tool system service.
    
    Returns:
        ToolSystemService instance (may be uninitialized)
    """
    global _tool_system_service
    if _tool_system_service is None:
        logger.warning("Tool system service not yet initialized")
        _tool_system_service = ToolSystemService()
    return _tool_system_service


def reset_tool_system() -> None:
    """Reset the tool system (useful for testing)."""
    global _tool_system_service
    _tool_system_service = None
    from app.tools import reset_tool_registry
    reset_tool_registry()
    logger.info("Tool system reset")

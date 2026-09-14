"""
Tool System Initialization.

Bootstraps the unified tool registry by registering all available tools.
Adapts existing runners (BrowserRunner, ResearchRunner, etc.) to the Tool interface.
"""

import logging
from typing import Optional

from app.tools.artifact_generation_tool import ArtifactGenerationTool
from app.tools.registry import get_tool_registry
from app.tools.adapters import RunnerAsToolAdapter
from app.tools.contract import ToolCategory

logger = logging.getLogger(__name__)


def initialize_tool_registry(
    runners_registry: Optional[dict] = None,
    include_research: bool = True,
    include_browser: bool = True,
    include_writing: bool = True,
    include_communication: bool = True,
    include_calendar: bool = True,
    include_file: bool = True,
) -> None:
    """
    Initialize the tool registry with all available tools.
    
    Adapts existing execution runners to the unified Tool interface
    and registers them in the global tool registry.
    
    Args:
        runners_registry: Pre-initialized RunnerRegistry with runner instances
        include_*: Flags to include specific tool categories
    """
    registry = get_tool_registry()

    # Register built-in artifact generation tool independently of the runner registry.
    artifact_tool = ArtifactGenerationTool()
    try:
        registry.register(artifact_tool)
        logger.info("Registered artifact generation tool")
    except ValueError as e:
        logger.warning(f"Could not register artifact generation tool: {e}")

    if runners_registry is None:
        logger.warning("No runners_registry provided to initialize_tool_registry; built-ins remain available")
        return

    # Register Research tool
    if include_research and runners_registry.get("research"):
        research_runner = runners_registry.get("research")
        research_tool = RunnerAsToolAdapter(
            runner_name="web_search",
            runner_instance=research_runner,
            category=ToolCategory.RESEARCH,
            description="Search the web, fetch pages, and compile research findings",
            timeout_seconds=120,
            max_retries=2,
        )
        try:
            registry.register(research_tool)
            logger.info("Registered research tool")
        except ValueError as e:
            logger.warning(f"Could not register research tool: {e}")
    
    # Register Browser tool
    if include_browser and runners_registry.get("browser"):
        browser_runner = runners_registry.get("browser")
        browser_tool = RunnerAsToolAdapter(
            runner_name="browser_automation",
            runner_instance=browser_runner,
            category=ToolCategory.BROWSER,
            description="Automate browser actions: navigate to URLs, interact with pages, extract content",
            timeout_seconds=180,
            max_retries=1,
        )
        try:
            registry.register(browser_tool)
            logger.info("Registered browser tool")
        except ValueError as e:
            logger.warning(f"Could not register browser tool: {e}")
    
    # Register Writing tool
    if include_writing and runners_registry.get("writing"):
        writing_runner = runners_registry.get("writing")
        writing_tool = RunnerAsToolAdapter(
            runner_name="writing",
            runner_instance=writing_runner,
            category=ToolCategory.WRITING,
            description="Generate, edit, and refine written content",
            timeout_seconds=120,
            max_retries=1,
        )
        try:
            registry.register(writing_tool)
            logger.info("Registered writing tool")
        except ValueError as e:
            logger.warning(f"Could not register writing tool: {e}")
    
    # Register Communication tool
    if include_communication and runners_registry.get("communication"):
        communication_runner = runners_registry.get("communication")
        communication_tool = RunnerAsToolAdapter(
            runner_name="communication",
            runner_instance=communication_runner,
            category=ToolCategory.COMMUNICATION,
            description="Send messages, emails, and collaborate with others",
            timeout_seconds=60,
            max_retries=2,
        )
        try:
            registry.register(communication_tool)
            logger.info("Registered communication tool")
        except ValueError as e:
            logger.warning(f"Could not register communication tool: {e}")
    
    # Register Calendar tool
    if include_calendar and runners_registry.get("calendar"):
        calendar_runner = runners_registry.get("calendar")
        calendar_tool = RunnerAsToolAdapter(
            runner_name="calendar",
            runner_instance=calendar_runner,
            category=ToolCategory.CALENDAR,
            description="Manage calendar events, meetings, and schedules",
            timeout_seconds=60,
            max_retries=1,
        )
        try:
            registry.register(calendar_tool)
            logger.info("Registered calendar tool")
        except ValueError as e:
            logger.warning(f"Could not register calendar tool: {e}")
    
    # Register File tool
    if include_file and runners_registry.get("file"):
        file_runner = runners_registry.get("file")
        file_tool = RunnerAsToolAdapter(
            runner_name="file_operations",
            runner_instance=file_runner,
            category=ToolCategory.FILE,
            description="Create, read, update, and manage files",
            timeout_seconds=120,
            max_retries=1,
        )
        try:
            registry.register(file_tool)
            logger.info("Registered file tool")
        except ValueError as e:
            logger.warning(f"Could not register file tool: {e}")
    
    # Log summary
    tools = registry.list_tools()
    logger.info(
        f"Tool registry initialized with {len(tools)} tools",
        extra={"count": len(tools), "tools": [t.name for t in tools]},
    )


def get_available_tools() -> list[dict[str, str]]:
    """
    Get list of available tools for discovery.
    
    Returns:
        List of tool definitions as dicts
    """
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

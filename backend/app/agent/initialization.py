"""
Tool registry initialization.

This module initializes the tool registry with all available tools
at application startup.
"""

import logging
from app.agent.registry import get_tool_registry
from app.agent.mock_tools import EchoTool, ConcatenateTool, CounterTool
from app.agent.tools import PDFGenerationTool, EmailTool, FileOperationsTool, DocumentGenerationTool, BrowserTool
from app.agent.tools.calendar_tool import CalendarListUpcomingEventsTool
from app.agent.tools.research_tool import ResearchTool
from app.core.config import get_settings
from app.email_provider.smtp_provider import SMTPEmailProvider
from app.email_provider.test_provider import TestEmailProvider

logger = logging.getLogger(__name__)


def initialize_tool_registry() -> None:
    """Initialize the global tool registry with all available tools."""
    registry = get_tool_registry()

    # Check if already initialized (idempotent)
    if registry.get_tool_names():
        logger.debug(f"Tool registry already initialized with {len(registry.get_tool_names())} tools")
        return

    # Register mock tools for testing
    registry.register(EchoTool())
    registry.register(ConcatenateTool())
    registry.register(CounterTool())

    # Register real tools
    registry.register(ResearchTool())
    registry.register(PDFGenerationTool())
    registry.register(FileOperationsTool())
    registry.register(DocumentGenerationTool())
    registry.register(BrowserTool())
    registry.register(CalendarListUpcomingEventsTool())

    settings = get_settings()
    smtp_provider = SMTPEmailProvider(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_username,
        smtp_password=settings.smtp_password,
        from_email=settings.smtp_from_email,
    )
    if smtp_provider.validate_configuration():
        registry.register(EmailTool(provider=smtp_provider))
        logger.info("Registered email tool with SMTP provider")
    else:
        registry.register(EmailTool(provider=TestEmailProvider()))
        logger.info("Registered email tool with test provider (SMTP not configured)")

    logger.info(f"Initialized tool registry with {len(registry.get_tool_names())} tools")
    logger.info(f"Available tools: {', '.join(registry.get_tool_names())}")



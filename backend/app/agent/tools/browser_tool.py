"""
Browser Tool for Agent Orchestrator.

This tool provides real web automation and interaction capabilities:
- Navigate to URLs
- Read and extract page content
- Click elements, fill forms
- Extract links, search web
- Take screenshots
- Multi-step workflows with session persistence

The tool uses Playwright for browser automation and BrowserSessionManager
for per-user session management.
"""

import logging
import os
from typing import Any, Optional
from uuid import uuid4

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema
from app.browser.service import BrowserService
from app.browser.session_manager import BrowserSessionManager

logger = logging.getLogger(__name__)


class BrowserTool(BaseTool):
    """Tool for real web automation and interaction."""

    def __init__(
        self,
        user_id: Optional[str] = None,
        headless: bool = True,
        browser_service: Optional[BrowserService] = None,
        session_manager: Optional[BrowserSessionManager] = None,
    ):
        super().__init__()
        self.user_id = user_id or "default_user"
        self.headless = headless
        self.browser_service = browser_service or BrowserService(headless=headless)
        self.session_manager = session_manager or BrowserSessionManager(
            user_id=self.user_id,
            headless=headless,
        )
        # In-memory session tracking for current execution
        self._active_sessions: dict[str, Any] = {}

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="browser",
            description=(
                "Real web browser automation and interaction. "
                "Supports navigating to URLs, reading/extracting page content, "
                "clicking elements, filling forms, extracting links, searching web, "
                "taking screenshots, and multi-step workflows with session persistence."
            ),
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "action": {
                        "type": "string",
                        "enum": [
                            "open_url",
                            "read_page",
                            "click",
                            "fill",
                            "extract_links",
                            "extract_headings",
                            "extract_tables",
                            "search",
                            "screenshot",
                            "close",
                        ],
                        "description": "The browser action to perform",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to (for open_url, search actions)",
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (for search action)",
                    },
                    "selector": {
                        "type": "string",
                        "description": "CSS selector for element (for click, fill actions)",
                    },
                    "value": {
                        "type": "string",
                        "description": "Value to fill (for fill action)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to reuse existing browser session (for multi-step workflows)",
                    },
                    "goal": {
                        "type": "string",
                        "description": "Goal/context for page analysis (for read_page action)",
                    },
                    "wait_for_load": {
                        "type": "boolean",
                        "description": "Wait for page to load (default: true)",
                        "default": True,
                    },
                },
                required=["action"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "success": {"type": "boolean"},
                    "action": {"type": "string"},
                    "session_id": {"type": "string"},
                    "result": {"type": "object"},
                    "page_state": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                    "error": {"type": "string"},
                },
            ),
            category="browser",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Execute browser action."""
        action = parameters.get("action")

        if not action:
            return self._error_result("action_required", "action parameter is required")

        try:
            logger.info(f"Executing browser action: {action}")

            # Get or create browser session
            session_id = parameters.get("session_id")
            if session_id and session_id in self._active_sessions:
                browser = self._active_sessions[session_id]["browser"]
                page = self._active_sessions[session_id]["page"]
            else:
                # Create new session
                session_id = str(uuid4())
                browser = await self.browser_service.launch_browser()
                page = await self.browser_service.open_page(browser)
                self._active_sessions[session_id] = {"browser": browser, "page": page}

            # Execute action
            if action == "open_url":
                result = await self._action_open_url(page, parameters)
            elif action == "read_page":
                result = await self._action_read_page(page, parameters)
            elif action == "click":
                result = await self._action_click(page, parameters)
            elif action == "fill":
                result = await self._action_fill(page, parameters)
            elif action == "extract_links":
                result = await self._action_extract_links(page, parameters)
            elif action == "extract_headings":
                result = await self._action_extract_headings(page, parameters)
            elif action == "extract_tables":
                result = await self._action_extract_tables(page, parameters)
            elif action == "search":
                result = await self._action_search(page, parameters)
            elif action == "screenshot":
                result = await self._action_screenshot(page, parameters)
            elif action == "close":
                result = await self._action_close(session_id, parameters)
            else:
                return self._error_result("invalid_action", f"Unknown action: {action}")

            # Get current page state
            page_state = await self._get_page_state(page) if action != "close" else {}

            return {
                "success": True,
                "action": action,
                "session_id": session_id,
                "result": result,
                "page_state": page_state,
            }

        except Exception as exc:
            logger.error(f"Browser action failed: {exc}")
            return self._error_result(str(type(exc).__name__), str(exc))

    async def _action_open_url(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Navigate to a URL."""
        url = parameters.get("url")
        if not url:
            raise ValueError("url parameter is required for open_url action")

        wait_for_load = parameters.get("wait_for_load", True)
        nav_result = await self.browser_service.navigate_to_url(
            page, url, wait_for_load=wait_for_load
        )

        return {
            "url": nav_result.get("url"),
            "status": nav_result.get("status"),
            "error": nav_result.get("error"),
        }

    async def _action_read_page(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Read and analyze current page content."""
        goal = parameters.get("goal")
        content = await self.browser_service.read_page_content(page, goal=goal)

        return {
            "url": content.get("url"),
            "title": content.get("title"),
            "visible_text": content.get("visible_text", "")[:5000],  # Truncate for size
            "headings": content.get("headings", []),
            "links_count": len(content.get("links", [])),
            "tables_count": len(content.get("tables", [])),
            "metadata": content.get("metadata", {}),
        }

    async def _action_click(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Click an element."""
        selector = parameters.get("selector")
        if not selector:
            raise ValueError("selector parameter is required for click action")

        await self.browser_service.click_element(page, selector)
        return {"selector": selector, "clicked": True}

    async def _action_fill(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Fill a form field."""
        selector = parameters.get("selector")
        value = parameters.get("value")

        if not selector:
            raise ValueError("selector parameter is required for fill action")
        if not value:
            raise ValueError("value parameter is required for fill action")

        await self.browser_service.fill_input(page, selector, value)
        return {"selector": selector, "value": value, "filled": True}

    async def _action_extract_links(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Extract all links from page."""
        links = await self.browser_service.extract_links(page)

        return {
            "links_count": len(links),
            "links": [
                {"text": link.get("text"), "href": link.get("href")} for link in links[:50]
            ],  # Limit to 50 links
        }

    async def _action_extract_headings(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Extract all headings from page."""
        headings = await self.browser_service.extract_headings(page)

        return {
            "headings_count": len(headings),
            "headings": headings[:30],  # Limit to 30 headings
        }

    async def _action_extract_tables(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Extract all tables from page."""
        tables = await self.browser_service.extract_tables(page)

        return {
            "tables_count": len(tables),
            "tables": tables[:5],  # Limit to 5 tables
        }

    async def _action_search(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Search on Google."""
        query = parameters.get("query")
        if not query:
            raise ValueError("query parameter is required for search action")

        result = await self.browser_service.search(page, query)
        return {"query": query, "url": result.get("url"), "error": result.get("error")}

    async def _action_screenshot(self, page: Any, parameters: dict[str, Any]) -> dict[str, Any]:
        """Take a screenshot."""
        output_path = os.path.join("/tmp", f"screenshot-{uuid4()}.png")
        path = await self.browser_service.take_screenshot(page, output_path=output_path)

        return {"screenshot_path": path, "taken": True}

    async def _action_close(self, session_id: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Close browser session."""
        if session_id in self._active_sessions:
            session = self._active_sessions[session_id]
            browser = session.get("browser")
            if browser:
                try:
                    await self.browser_service.close_browser(browser)
                except Exception as exc:
                    logger.warning(f"Error closing browser: {exc}")
            del self._active_sessions[session_id]

        return {"session_id": session_id, "closed": True}

    async def _get_page_state(self, page: Any) -> dict[str, Any]:
        """Get current page state."""
        try:
            url = page.url if hasattr(page, "url") else ""
            title_coro = page.title() if hasattr(page, "title") else None
            title = await title_coro if title_coro is not None else ""
            content = await self.browser_service.read_page_content(page)
            visible_text = content.get("visible_text", "")[:2000]  # Truncate

            return {
                "url": url,
                "title": title,
                "content": visible_text,
            }
        except Exception as exc:
            logger.warning(f"Error getting page state: {exc}")
            return {"url": "", "title": "", "content": ""}

    def _error_result(self, error_type: str, message: str) -> dict[str, Any]:
        """Create an error result."""
        return {
            "success": False,
            "action": "unknown",
            "session_id": None,
            "result": None,
            "page_state": {},
            "error": f"{error_type}: {message}",
        }

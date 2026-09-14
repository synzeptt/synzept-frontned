"""Connector framework package exports."""
from .base import Connector
from .context import ConnectorContext
from .registry import ConnectorRegistry, default_registry
from .manager import ConnectorManager
from .result import (
    ConnectorResult,
    AuthenticationResult,
    HealthResult,
    SearchResult,
    ReadResult,
    WriteResult,
    ExecutionMetrics,
    ActionResult,
)
from .google_account_connector import GoogleAccountConnector
from .gmail_connector import GmailConnector
from .google_calendar_connector import GoogleCalendarConnector
from .google_drive_connector import GoogleDriveConnector
from .google_workspace_content_connector import GoogleDocsConnector, GoogleSheetsConnector, GoogleSlidesConnector
from .http_fetch_connector import HTTPFetchConnector
from .web_search_connector import WebSearchConnector
from .browser_connector import BrowserConnector
from .errors import (
    ConnectorError,
    AuthenticationFailure,
    PermissionDenied,
    RateLimited,
    TimeoutError as ConnectorTimeout,
    NetworkFailure,
    ProviderError,
    ValidationFailure,
    RetryableFailure,
    FatalFailure,
)

__all__ = [
    "Connector",
    "ConnectorContext",
    "ConnectorRegistry",
    "default_registry",
    "ConnectorManager",
    "GoogleAccountConnector",
    "GmailConnector",
    "GoogleCalendarConnector",
    "GoogleDriveConnector",
    "GoogleDocsConnector",
    "GoogleSheetsConnector",
    "GoogleSlidesConnector",
    "HTTPFetchConnector",
    "WebSearchConnector",
    "ActionResult",
]

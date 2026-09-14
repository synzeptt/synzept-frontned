"""Base email provider interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class EmailMessage:
    """Represents an email message to send."""
    recipient: str
    subject: str
    body: str
    attachments: list[dict[str, Any]] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []


@dataclass
class EmailResult:
    """Result of an email send operation."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class BaseEmailProvider(ABC):
    """Abstract base class for email providers."""

    @abstractmethod
    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Send an email message.
        
        Args:
            message: EmailMessage with recipient, subject, body, attachments
            
        Returns:
            EmailResult with success status and optional message_id or error
        """
        pass

    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Validate that the provider is properly configured.
        
        Returns:
            True if provider can send emails, False if configuration is missing
        """
        pass

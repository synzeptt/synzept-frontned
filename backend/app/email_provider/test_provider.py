"""Test email provider for deterministic testing."""

import logging
from typing import Any
import uuid

from app.email_provider.base_provider import BaseEmailProvider, EmailMessage, EmailResult

logger = logging.getLogger(__name__)


class TestEmailProvider(BaseEmailProvider):
    """
    Test provider that simulates email sends without actually sending.
    
    Useful for testing and development. Never sends real emails.
    """

    def __init__(self):
        """Initialize test provider."""
        self.sent_emails = []  # Track sent emails for assertions
        self.should_fail = False  # Can be set to simulate failures

    def validate_configuration(self) -> bool:
        """Test provider is always configured."""
        return True

    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Simulate sending an email.
        
        Args:
            message: EmailMessage to send
            
        Returns:
            EmailResult with simulated success or failure
        """
        if self.should_fail:
            error_msg = "Simulated email send failure"
            logger.info(f"Simulated email failure to {message.recipient}: {error_msg}")
            return EmailResult(
                success=False,
                error=error_msg,
                details={"reason": "simulated_failure"},
            )

        # Simulate successful send
        message_id = str(uuid.uuid4())
        self.sent_emails.append({
            "recipient": message.recipient,
            "subject": message.subject,
            "body": message.body,
            "attachments": message.attachments,
            "message_id": message_id,
        })

        logger.info(f"Simulated email sent to {message.recipient} (ID: {message_id})")
        return EmailResult(
            success=True,
            message_id=message_id,
            details={
                "to": message.recipient,
                "subject": message.subject,
                "attachment_count": len(message.attachments),
            },
        )

    def get_sent_emails(self) -> list[dict[str, Any]]:
        """Get list of emails sent in this test session."""
        return self.sent_emails

    def reset(self) -> None:
        """Reset the test provider state."""
        self.sent_emails = []
        self.should_fail = False

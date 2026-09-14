"""Email provider abstraction for Synzept."""

from app.email_provider.base_provider import BaseEmailProvider, EmailResult, EmailMessage
from app.email_provider.smtp_provider import SMTPEmailProvider
from app.email_provider.test_provider import TestEmailProvider

__all__ = [
    "BaseEmailProvider",
    "EmailResult",
    "EmailMessage",
    "SMTPEmailProvider",
    "TestEmailProvider",
]

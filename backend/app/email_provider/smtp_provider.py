"""SMTP-based email provider for production use."""

import logging
import os
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Any

from app.email_provider.base_provider import BaseEmailProvider, EmailMessage, EmailResult

logger = logging.getLogger(__name__)


class SMTPEmailProvider(BaseEmailProvider):
    """Email provider using SMTP (production-ready)."""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        smtp_user: str | None = None,
        smtp_password: str | None = None,
        from_email: str | None = None,
    ):
        """
        Initialize SMTP provider.
        
        Args:
            smtp_host: SMTP server host (default from env var SMTP_HOST)
            smtp_port: SMTP server port (default from env var SMTP_PORT, default 587)
            smtp_user: SMTP username (default from env var SMTP_USER)
            smtp_password: SMTP password (default from env var SMTP_PASSWORD)
            from_email: Sender email address (default from env var FROM_EMAIL)
        """
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("FROM_EMAIL")

    def validate_configuration(self) -> bool:
        """Check if SMTP is properly configured."""
        required = [self.smtp_host, self.smtp_port, self.smtp_user, self.smtp_password, self.from_email]
        if all(required):
            return True
        missing = []
        if not self.smtp_host:
            missing.append("SMTP_HOST")
        if not self.smtp_port:
            missing.append("SMTP_PORT")
        if not self.smtp_user:
            missing.append("SMTP_USER")
        if not self.smtp_password:
            missing.append("SMTP_PASSWORD")
        if not self.from_email:
            missing.append("FROM_EMAIL")
        logger.warning(f"SMTP provider not configured. Missing: {', '.join(missing)}")
        return False

    async def send(self, message: EmailMessage) -> EmailResult:
        """
        Send email via SMTP.
        
        Args:
            message: EmailMessage to send
            
        Returns:
            EmailResult with success status
        """
        if not self.validate_configuration():
            return EmailResult(
                success=False,
                error="SMTP provider is not properly configured",
                details={"reason": "missing_configuration"},
            )

        try:
            # Create MIME message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = message.recipient
            msg["Subject"] = message.subject

            # Add body
            msg.attach(MIMEText(message.body, "plain"))

            # Add attachments
            for attachment in message.attachments:
                await self._add_attachment(msg, attachment)

            # Send via SMTP
            try:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                message_id = server.send_message(msg)
                server.quit()

                logger.info(f"Email sent successfully to {message.recipient}")
                return EmailResult(
                    success=True,
                    message_id=str(message_id),
                    details={"to": message.recipient, "subject": message.subject},
                )
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error while sending to {message.recipient}: {str(e)}")
                return EmailResult(
                    success=False,
                    error=f"SMTP error: {type(e).__name__}",
                    details={"reason": "smtp_error", "error_type": type(e).__name__},
                )

        except Exception as e:
            logger.error(f"Error sending email to {message.recipient}: {str(e)}", exc_info=True)
            return EmailResult(
                success=False,
                error=f"Email send failed: {type(e).__name__}",
                details={"reason": "send_failed", "error_type": type(e).__name__},
            )

    async def _add_attachment(self, msg: MIMEMultipart, attachment: dict[str, Any]) -> None:
        """
        Add an attachment to the MIME message.
        
        Args:
            msg: MIME message to add attachment to
            attachment: Attachment dict with 'file_path' or 'filename' and optional 'content_type'
        """
        file_path = attachment.get("file_path") or attachment.get("path")
        if not file_path:
            logger.warning(f"Attachment missing file_path: {attachment}")
            return

        if not os.path.exists(file_path):
            logger.warning(f"Attachment file not found: {file_path}")
            return

        try:
            filename = attachment.get("filename") or os.path.basename(file_path)
            content_type = attachment.get("content_type") or "application/octet-stream"

            with open(file_path, "rb") as f:
                attachment_data = f.read()

            if content_type.startswith("text/"):
                part = MIMEText(attachment_data.decode("utf-8"), _subtype=content_type.split("/")[1])
            elif content_type.startswith("image/"):
                part = MIMEBase("image", content_type.split("/")[1])
                part.set_payload(attachment_data)
            elif content_type.startswith("application/pdf"):
                part = MIMEApplication(attachment_data, "pdf")
            else:
                part = MIMEBase(*content_type.split("/", 1))
                part.set_payload(attachment_data)

            part.add_header("Content-Disposition", "attachment", filename=filename)
            msg.attach(part)
            logger.debug(f"Attached file: {filename}")

        except Exception as e:
            logger.error(f"Error attaching file {file_path}: {str(e)}", exc_info=True)

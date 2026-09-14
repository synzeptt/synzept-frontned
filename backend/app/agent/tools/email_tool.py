"""Email Tool for Agent Orchestrator."""

import logging
from typing import Any, Optional
from uuid import UUID

from app.agent.tool import BaseTool
from app.agent.models import ToolDefinition, ToolInputSchema, ToolOutputSchema
from app.email_provider.base_provider import BaseEmailProvider, EmailMessage
from app.email_provider.smtp_provider import SMTPEmailProvider

logger = logging.getLogger(__name__)


class EmailTool(BaseTool):
    """Tool for sending emails with optional attachments."""

    def __init__(self, provider: Optional[BaseEmailProvider] = None):
        """
        Initialize email tool.
        
        Args:
            provider: Email provider (defaults to SMTP)
        """
        super().__init__()
        self.provider = provider or SMTPEmailProvider()

    def get_definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="email",
            description=(
                "Send an email to a recipient with optional attachments. "
                "The email is sent only after confirmation. "
                "Can attach files from previous workflow steps."
            ),
            input_schema=ToolInputSchema(
                type="object",
                properties={
                    "recipient": {
                        "type": "string",
                        "description": "Email address of recipient"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Subject line for the email"
                    },
                    "body": {
                        "type": "string",
                        "description": "Body text of the email (plain text or markdown)"
                    },
                    "attachments": {
                        "type": "array",
                        "description": "List of file attachments",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "Path to the file to attach"
                                },
                                "filename": {
                                    "type": "string",
                                    "description": "Name to use for the attachment"
                                },
                                "content_type": {
                                    "type": "string",
                                    "description": "MIME type (e.g., application/pdf)"
                                }
                            }
                        }
                    }
                },
                required=["recipient", "subject", "body"],
            ),
            output_schema=ToolOutputSchema(
                type="object",
                properties={
                    "success": {"type": "boolean"},
                    "message_id": {"type": "string"},
                    "recipient": {"type": "string"},
                    "subject": {"type": "string"},
                    "error": {"type": "string"},
                },
            ),
            category="communication",
        )

    async def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """
        Send email using the configured provider.
        
        Args:
            parameters: Must include recipient, subject, body; optionally attachments
            
        Returns:
            Dict with success status and optional message_id or error
        """
        recipient = parameters.get("recipient", "").strip()
        subject = parameters.get("subject", "").strip()
        body = parameters.get("body", "").strip()
        attachments = parameters.get("attachments", []) or []

        # Validate inputs
        if not recipient:
            return {
                "success": False,
                "message_id": None,
                "recipient": None,
                "subject": None,
                "error": "Missing recipient email address",
            }

        if not subject:
            return {
                "success": False,
                "message_id": None,
                "recipient": recipient,
                "subject": None,
                "error": "Missing email subject",
            }

        if not body:
            return {
                "success": False,
                "message_id": None,
                "recipient": recipient,
                "subject": subject,
                "error": "Missing email body",
            }

        # Validate recipient format
        if "@" not in recipient or "." not in recipient.split("@")[1]:
            return {
                "success": False,
                "message_id": None,
                "recipient": recipient,
                "subject": subject,
                "error": f"Invalid email address: {recipient}",
            }

        # Create email message
        message = EmailMessage(
            recipient=recipient,
            subject=subject,
            body=body,
            attachments=attachments,
        )

        # Send via provider
        try:
            logger.info(f"Sending email to {recipient} with subject: {subject}")
            result = await self.provider.send(message)

            if result.success:
                logger.info(f"Email sent successfully (ID: {result.message_id})")
                return {
                    "success": True,
                    "message_id": result.message_id,
                    "recipient": recipient,
                    "subject": subject,
                    "error": None,
                }
            else:
                logger.error(f"Email send failed: {result.error}")
                return {
                    "success": False,
                    "message_id": None,
                    "recipient": recipient,
                    "subject": subject,
                    "error": result.error,
                }

        except Exception as e:
            logger.error(f"Email send exception: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message_id": None,
                "recipient": recipient,
                "subject": subject,
                "error": f"Email send failed: {type(e).__name__}: {str(e)}",
            }

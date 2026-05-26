import logging
import smtplib
from email.message import EmailMessage
from html import escape

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailService:
    def send_password_reset(self, *, email: str, reset_url: str, expires_minutes: int) -> None:
        subject = "Reset your Synzept password"
        text = (
            "Hi,\n\n"
            "We received a request to reset your Synzept password.\n\n"
            f"Use this secure link within {expires_minutes} minutes:\n{reset_url}\n\n"
            "If you did not ask for this, you can leave this email as it is. Your account will stay unchanged.\n\n"
            "Synzept"
        )
        safe_reset_url = escape(reset_url, quote=True)
        html = f"""
        <div style="font-family:Arial,sans-serif;color:#292524;line-height:1.6">
          <p>Hi,</p>
          <p>We received a request to reset your Synzept password.</p>
          <p><a href="{safe_reset_url}" style="color:#57534e">Reset your password</a></p>
          <p>This link stays available for {expires_minutes} minutes.</p>
          <p>If you did not ask for this, you can leave this email as it is. Your account will stay unchanged.</p>
          <p>Synzept</p>
        </div>
        """
        self._send(email=email, subject=subject, text=text, html=html)

    def _send(self, *, email: str, subject: str, text: str, html: str) -> None:
        if not settings.smtp_host:
            logger.info("password reset email prepared; configure SMTP_HOST to deliver", extra={"recipient": email, "subject": subject})
            return

        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = email
        message["Subject"] = subject
        message.set_content(text)
        message.add_alternative(html, subtype="html")

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)

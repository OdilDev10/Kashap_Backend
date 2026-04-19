"""Email service for sending emails via Resend."""

import logging
from app.config import settings
from app.services.email_templates import (
    get_verification_email_html,
    get_password_reset_email_html,
    get_otp_email_html,
    get_welcome_email_html,
)

logger = logging.getLogger("app.email")


class EmailService:
    """Service for sending emails via Resend API."""

    def __init__(self):
        self.api_key = settings.mail_resend_api_key
        self.from_email = settings.mail_from_email
        self.from_name = settings.mail_from_name
        self.support_email = settings.support_inbox_email
        self.app_name = "OptiCredit"
        self.app_url = settings.app_url

    async def _send_via_resend(
        self, to_email: str, subject: str, html_content: str
    ) -> bool:
        """Send email via Resend API."""
        try:
            import resend

            resend.api_key = self.api_key

            params = {
                "from": f"{self.from_name} <{self.from_email}>",
                "to": to_email,
                "subject": subject,
                "html": html_content,
            }

            response = resend.Emails.send(params)  # type: ignore
            logger.info(f"[EMAIL] Sent to {to_email}, subject: {subject}")
            return True

        except Exception as e:
            logger.error(f"[EMAIL] Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_verification_email(
        self, to_email: str, token: str, recipient_name: str = "Usuario"
    ) -> bool:
        """Send email verification link to user."""
        verification_link = f"{self.app_url}/verify-email?token={token}"

        html_content = get_verification_email_html(
            recipient_name=recipient_name,
            verification_link=verification_link,
            app_name=self.app_name,
        )

        subject = "Verifica tu correo electrónico - OptiCredit"

        if settings.environment == "development":
            logger.info(f"[EMAIL DEV] To: {to_email}")
            logger.info(f"[EMAIL DEV] Subject: {subject}")
            logger.info(f"[EMAIL DEV] Link: {verification_link}")
            return True

        return await self._send_via_resend(to_email, subject, html_content)

    async def send_password_reset_email(
        self, to_email: str, token: str, recipient_name: str = "Usuario"
    ) -> bool:
        """Send password reset link to user."""
        reset_link = f"{self.app_url}/reset-password?token={token}"

        html_content = get_password_reset_email_html(
            recipient_name=recipient_name, reset_link=reset_link, app_name=self.app_name
        )

        subject = "Restablecer Contraseña - OptiCredit"

        if settings.environment == "development":
            logger.info(f"[EMAIL DEV] To: {to_email}")
            logger.info(f"[EMAIL DEV] Subject: {subject}")
            logger.info(f"[EMAIL DEV] Link: {reset_link}")
            return True

        return await self._send_via_resend(to_email, subject, html_content)

    async def send_otp_email(
        self, to_email: str, otp_code: str, recipient_name: str = "Usuario"
    ) -> bool:
        """Send OTP code to user."""
        html_content = get_otp_email_html(
            recipient_name=recipient_name, otp_code=otp_code, app_name=self.app_name
        )

        subject = "Tu código de verificación - OptiCredit"

        if settings.environment == "development":
            logger.info(f"[EMAIL DEV] To: {to_email}")
            logger.info(f"[EMAIL DEV] Subject: {subject}")
            logger.info(f"[EMAIL DEV] OTP: {otp_code}")
            return True

        return await self._send_via_resend(to_email, subject, html_content)

    async def send_welcome_email(
        self, to_email: str, recipient_name: str = "Usuario"
    ) -> bool:
        """Send welcome email after email verification."""
        html_content = get_welcome_email_html(
            recipient_name=recipient_name, app_name=self.app_name, app_url=self.app_url
        )

        subject = "Bienvenido/a a OptiCredit"

        if settings.environment == "development":
            logger.info(f"[EMAIL DEV] To: {to_email}")
            logger.info(f"[EMAIL DEV] Subject: {subject}")
            return True

        return await self._send_via_resend(to_email, subject, html_content)

    async def send_email(
        self, to_email: str, subject: str, body: str, is_html: bool = False
    ) -> bool:
        """Send generic email."""
        if not is_html:
            body = f"<html><body><pre style='font-family: monospace;'>{body}</pre></body></html>"

        if settings.environment == "development":
            logger.info(f"[EMAIL DEV] To: {to_email}")
            logger.info(f"[EMAIL DEV] Subject: {subject}")
            logger.info(f"[EMAIL DEV] Body: {body[:200]}...")
            return True

        return await self._send_via_resend(to_email, subject, body)

    async def send_support_request(
        self, name: str, email: str, subject: str, message: str
    ) -> bool:
        """Send support request to support inbox."""
        html_content = f"""
        <html>
        <body>
            <h2>New Support Request</h2>
            <p><strong>Name:</strong> {name}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Subject:</strong> {subject}</p>
            <hr>
            <p><strong>Message:</strong></p>
            <pre>{message}</pre>
        </body>
        </html>
        """

        if settings.environment == "development":
            logger.info(f"[EMAIL DEV] Support request from {email}")
            logger.info(f"[EMAIL DEV] Subject: {subject}")
            return True

        return await self._send_via_resend(
            self.support_email, f"Support: {subject}", html_content
        )


email_service = EmailService()

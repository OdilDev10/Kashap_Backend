"""SMS service for sending OTP codes via SMS using Twilio."""

import logging
from typing import Optional

from app.config import settings
from app.core.exceptions import ApplicationException

logger = logging.getLogger(__name__)

# Twilio client (lazy loaded)
twilio_client: Optional[object] = None


def initialize_sms():
    """Initialize Twilio client (called conditionally based on config)."""
    global twilio_client
    if not settings.sms_enabled:
        logger.info("SMS service disabled")
        return

    try:
        from twilio.rest import Client

        twilio_client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        logger.info("Twilio SMS service initialized")
    except ImportError:
        logger.warning("Twilio not installed, SMS service unavailable")
    except Exception as e:
        logger.error(f"Failed to initialize Twilio: {str(e)}")


async def send_otp_sms(phone_number: str, otp_code: str) -> dict:
    """
    Send OTP code via SMS using Twilio.

    Args:
        phone_number: Recipient phone number (international format: +1234567890)
        otp_code: 6-digit OTP code

    Returns:
        dict with: {
            "success": bool,
            "message_sid": str (if successful),
            "error": str (if failed)
        }
    """
    if not settings.sms_enabled or twilio_client is None:
        return {
            "success": False,
            "error": "SMS service is not configured or enabled",
        }

    try:
        # Format message
        message_body = f"Tu código de verificación es: {otp_code}. No compartas este código."

        # Send via Twilio
        message = twilio_client.messages.create(
            body=message_body,
            from_=settings.twilio_phone_number,
            to=phone_number,
        )

        logger.info(f"OTP SMS sent to {phone_number}, SID: {message.sid}")

        return {
            "success": True,
            "message_sid": message.sid,
        }

    except Exception as e:
        logger.error(f"Failed to send OTP SMS to {phone_number}: {str(e)}")
        return {
            "success": False,
            "error": f"SMS send failed: {str(e)}",
        }


async def send_verification_sms(phone_number: str, verification_code: str) -> dict:
    """
    Send account verification SMS.

    Args:
        phone_number: Recipient phone number
        verification_code: Verification code

    Returns:
        dict with success status and message_sid or error
    """
    if not settings.sms_enabled or twilio_client is None:
        return {
            "success": False,
            "error": "SMS service is not configured",
        }

    try:
        message_body = (
            f"Tu código de verificación de cuenta es: {verification_code}. "
            f"Este código expira en 24 horas."
        )

        message = twilio_client.messages.create(
            body=message_body,
            from_=settings.twilio_phone_number,
            to=phone_number,
        )

        logger.info(f"Verification SMS sent to {phone_number}")

        return {
            "success": True,
            "message_sid": message.sid,
        }

    except Exception as e:
        logger.error(f"Failed to send verification SMS: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


async def send_notification_sms(phone_number: str, message_text: str) -> dict:
    """
    Send generic notification SMS.

    Args:
        phone_number: Recipient phone number
        message_text: Message content

    Returns:
        dict with success status
    """
    if not settings.sms_enabled or twilio_client is None:
        return {
            "success": False,
            "error": "SMS service not available",
        }

    try:
        message = twilio_client.messages.create(
            body=message_text,
            from_=settings.twilio_phone_number,
            to=phone_number,
        )

        return {
            "success": True,
            "message_sid": message.sid,
        }

    except Exception as e:
        logger.error(f"Failed to send notification SMS: {str(e)}")
        return {
            "success": False,
            "error": str(e),
        }


# Singleton instance
sms_service = None


def get_sms_service():
    """Factory to get SMS service (lazy initialization)."""
    global sms_service
    if sms_service is None:
        initialize_sms()
    return sms_service

"""Email templates for OptiCredit."""

from app.services.email_templates.base import render_template, BASE_TEMPLATE
from app.services.email_templates.verification import get_verification_email_html
from app.services.email_templates.password_reset import get_password_reset_email_html
from app.services.email_templates.otp import get_otp_email_html
from app.services.email_templates.welcome import get_welcome_email_html

__all__ = [
    "render_template",
    "BASE_TEMPLATE",
    "get_verification_email_html",
    "get_password_reset_email_html",
    "get_otp_email_html",
    "get_welcome_email_html",
]

"""Braintree payment service for subscriptions."""

import logging
from typing import Optional
from datetime import datetime

from app.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

# Braintree client (lazy loaded)
braintree_client = None


def initialize_braintree():
    """Initialize Braintree client."""
    global braintree_client
    try:
        import braintree

        braintree.Configuration.configure(
            braintree.Environment.Sandbox if settings.environment == "development" else braintree.Environment.Production,
            merchant_id=settings.braintree_merchant_id,
            public_key=settings.braintree_public_key,
            private_key=settings.braintree_private_key,
        )
        braintree_client = braintree
        logger.info("Braintree client initialized")
    except ImportError:
        logger.warning("Braintree not installed")
        raise AppException("Braintree SDK not available", code="BRAINTREE_NOT_INSTALLED")
    except Exception as e:
        logger.error(f"Failed to initialize Braintree: {str(e)}")
        raise AppException(f"Braintree initialization failed: {str(e)}", code="BRAINTREE_INIT_ERROR")


async def generate_client_token(customer_id: Optional[str] = None) -> str:
    """
    Generate Braintree client token for frontend.

    Args:
        customer_id: Optional Braintree customer ID

    Returns:
        Client token string
    """
    if braintree_client is None:
        initialize_braintree()

    try:
        if customer_id:
            result = braintree_client.ClientToken.generate({"customer_id": customer_id})
        else:
            result = braintree_client.ClientToken.generate()

        if result.is_success:
            return result.client_token
        else:
            raise AppException("Failed to generate client token", code="CLIENT_TOKEN_ERROR")

    except Exception as e:
        logger.error(f"Failed to generate Braintree client token: {str(e)}")
        raise AppException(f"Client token generation failed: {str(e)}", code="CLIENT_TOKEN_ERROR")


async def create_subscription(
    customer_id: str,
    plan_id: str,
    payment_method_nonce: str,
    billing_period_start_date: Optional[str] = None,
) -> dict:
    """
    Create Braintree subscription.

    Args:
        customer_id: Lender ID
        plan_id: Braintree plan ID (e.g., "starter", "professional")
        payment_method_nonce: Nonce from client token
        billing_period_start_date: Optional start date for billing

    Returns:
        Subscription data with subscription ID
    """
    if braintree_client is None:
        initialize_braintree()

    try:
        subscription_params = {
            "payment_method_nonce": payment_method_nonce,
            "plan_id": plan_id,
        }

        if billing_period_start_date:
            subscription_params["billing_period_start_date"] = billing_period_start_date

        result = braintree_client.Subscription.create(subscription_params)

        if result.is_success:
            subscription = result.subscription
            logger.info(f"Subscription created: {subscription.id}")

            return {
                "success": True,
                "subscription_id": subscription.id,
                "plan_id": subscription.plan_id,
                "status": subscription.status,
                "balance": float(subscription.balance),
                "created_at": subscription.created_at.isoformat(),
            }
        else:
            error_msg = str(result.errors)
            logger.error(f"Braintree subscription creation failed: {error_msg}")
            raise AppException(f"Subscription creation failed: {error_msg}", code="SUBSCRIPTION_ERROR")

    except Exception as e:
        logger.error(f"Exception creating Braintree subscription: {str(e)}")
        raise AppException(f"Subscription creation failed: {str(e)}", code="SUBSCRIPTION_ERROR")


async def get_subscription(subscription_id: str) -> dict:
    """Get subscription details."""
    if braintree_client is None:
        initialize_braintree()

    try:
        subscription = braintree_client.Subscription.find(subscription_id)

        return {
            "subscription_id": subscription.id,
            "plan_id": subscription.plan_id,
            "status": subscription.status,
            "balance": float(subscription.balance),
            "billing_period_start_date": subscription.billing_period_start_date.isoformat() if subscription.billing_period_start_date else None,
            "billing_period_end_date": subscription.billing_period_end_date.isoformat() if subscription.billing_period_end_date else None,
            "next_billing_date": subscription.next_billing_date.isoformat() if subscription.next_billing_date else None,
        }

    except Exception as e:
        logger.error(f"Failed to get subscription: {str(e)}")
        raise AppException(f"Subscription not found: {str(e)}", code="SUBSCRIPTION_NOT_FOUND")


async def cancel_subscription(subscription_id: str) -> dict:
    """Cancel a subscription."""
    if braintree_client is None:
        initialize_braintree()

    try:
        result = braintree_client.Subscription.cancel(subscription_id)

        if result.is_success:
            logger.info(f"Subscription cancelled: {subscription_id}")
            return {"success": True, "message": f"Subscription {subscription_id} cancelled"}
        else:
            raise AppException("Failed to cancel subscription", code="CANCEL_ERROR")

    except Exception as e:
        logger.error(f"Failed to cancel subscription: {str(e)}")
        raise AppException(f"Cancellation failed: {str(e)}", code="CANCEL_ERROR")


async def handle_webhook(bt_signature: str, bt_payload: str) -> dict:
    """
    Handle Braintree webhook.

    Args:
        bt_signature: Braintree webhook signature
        bt_payload: Braintree webhook payload

    Returns:
        Webhook event data
    """
    if braintree_client is None:
        initialize_braintree()

    try:
        webhook_notification = braintree_client.WebhookNotification.parse(bt_signature, bt_payload)

        logger.info(f"Webhook received: {webhook_notification.kind}")

        # Handle different webhook events
        if webhook_notification.kind == "subscription_charged_successfully":
            return {
                "event": "subscription_charged_successfully",
                "subscription_id": webhook_notification.subscription.id,
                "amount": str(webhook_notification.subscription.balance),
                "timestamp": datetime.now().isoformat(),
            }

        elif webhook_notification.kind == "subscription_charged_unsuccessfully":
            return {
                "event": "subscription_charged_unsuccessfully",
                "subscription_id": webhook_notification.subscription.id,
                "error": str(webhook_notification.subscription.failure_count),
                "timestamp": datetime.now().isoformat(),
            }

        elif webhook_notification.kind == "subscription_expired":
            return {
                "event": "subscription_expired",
                "subscription_id": webhook_notification.subscription.id,
                "timestamp": datetime.now().isoformat(),
            }

        else:
            return {
                "event": webhook_notification.kind,
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"Failed to parse webhook: {str(e)}")
        raise AppException(f"Webhook parsing failed: {str(e)}", code="WEBHOOK_ERROR")

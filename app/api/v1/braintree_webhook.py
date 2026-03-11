"""Braintree webhook and payment endpoints."""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, get_lender_context
from app.services.braintree_service import (
    generate_client_token,
    create_subscription,
    get_subscription,
    handle_webhook,
)
from app.models.user import User
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class ClientTokenResponse(BaseModel):
    """Client token response."""

    client_token: str


class SubscriptionCreateRequest(BaseModel):
    """Create subscription request."""

    plan_id: str
    payment_method_nonce: str
    billing_period_start_date: str | None = None


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    success: bool
    subscription_id: str
    plan_id: str
    status: str
    balance: float


@router.post("/braintree/client-token")
async def get_braintree_client_token(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Generate Braintree client token for payment form.

    Returns client token for Braintree hosted fields.
    """
    try:
        token = await generate_client_token(customer_id=str(current_user.lender_id))
        return {"client_token": token}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/braintree/create")
async def create_braintree_subscription(
    request: SubscriptionCreateRequest = Body(...),
    current_user: User = Depends(get_current_user),
    lender_id: str = Depends(get_lender_context),
) -> SubscriptionResponse:
    """
    Create Braintree subscription for lender.

    Requires:
    - plan_id: Braintree plan ID (e.g., "starter", "professional")
    - payment_method_nonce: Nonce from Braintree hosted fields
    - billing_period_start_date: Optional start date
    """
    try:
        result = await create_subscription(
            customer_id=lender_id,
            plan_id=request.plan_id,
            payment_method_nonce=request.payment_method_nonce,
            billing_period_start_date=request.billing_period_start_date,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/braintree/{subscription_id}")
async def get_braintree_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get subscription details from Braintree."""
    try:
        return await get_subscription(subscription_id)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/webhooks/braintree")
async def braintree_webhook(
    bt_signature: str = Body(...),
    bt_payload: str = Body(...),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """
    Handle Braintree webhooks.

    Receives webhook notifications from Braintree:
    - subscription_charged_successfully
    - subscription_charged_unsuccessfully
    - subscription_expired
    """
    try:
        webhook_data = await handle_webhook(bt_signature, bt_payload)

        # TODO: Update subscription status in database based on webhook event

        return MessageResponse(
            message=f"Webhook processed: {webhook_data.get('event', 'unknown')}"
        )
    except Exception as e:
        # Log but return 200 to acknowledge webhook received
        import logging
        logging.error(f"Webhook error: {str(e)}")
        return MessageResponse(message="Webhook received")

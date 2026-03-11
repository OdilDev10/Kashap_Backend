"""Payment management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from decimal import Decimal

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.payment_service import PaymentService
from app.services.voucher_service import VoucherService
from app.core.exceptions import AppException

router = APIRouter(prefix="/payments", tags=["payments"])


class SubmitPaymentRequest(BaseModel):
    """Submit payment request."""
    loan_id: str
    installment_id: str
    amount: Decimal = Field(..., gt=0)


class ApprovePaymentRequest(BaseModel):
    """Approve payment request."""
    review_notes: str | None = None


class RejectPaymentRequest(BaseModel):
    """Reject payment request."""
    review_notes: str


@router.post("/submit")
async def submit_payment(
    request: SubmitPaymentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Submit payment for installment."""
    try:
        service = PaymentService(session)
        result = await service.submit_payment(
            request.loan_id,
            request.installment_id,
            current_user.id,
            current_user.lender_id,
            request.amount,
            current_user.id,
        )
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{payment_id}/submit-for-review")
async def submit_for_review(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Submit payment for review after vouchers uploaded."""
    try:
        service = PaymentService(session)
        result = await service.submit_for_review(payment_id, current_user.lender_id)
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{payment_id}/approve")
async def approve_payment(
    payment_id: str,
    request: ApprovePaymentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Approve payment."""
    try:
        service = PaymentService(session)
        result = await service.approve_payment(
            payment_id, current_user.lender_id, current_user.id, request.review_notes
        )
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{payment_id}/reject")
async def reject_payment(
    payment_id: str,
    request: RejectPaymentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Reject payment."""
    try:
        service = PaymentService(session)
        result = await service.reject_payment(
            payment_id, current_user.lender_id, current_user.id, request.review_notes
        )
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get payment details with vouchers."""
    try:
        service = PaymentService(session)
        result = await service.get_payment_details(payment_id, current_user.lender_id)
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/")
async def list_pending_payments(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List payments pending review."""
    try:
        service = PaymentService(session)
        result = await service.list_pending_payments(current_user.lender_id, limit)
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{payment_id}/vouchers/upload")
async def upload_voucher(
    payment_id: str,
    file: UploadFile = File(...),
    upload_source: str = "web",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Upload voucher image for payment."""
    try:
        if not file.content_type.startswith("image/"):
            raise AppException("File must be an image")

        file_content = await file.read()
        service = VoucherService(session)
        result = await service.upload_voucher(
            payment_id,
            file_content,
            file.filename,
            file.content_type,
            upload_source,
            current_user.lender_id,
        )
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{payment_id}/vouchers")
async def list_vouchers(
    payment_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List vouchers for payment."""
    try:
        service = VoucherService(session)
        result = await service.list_vouchers_for_payment(payment_id, current_user.lender_id)
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/vouchers/{voucher_id}")
async def get_voucher_details(
    voucher_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get voucher details with OCR results."""
    try:
        service = VoucherService(session)
        result = await service.get_voucher_details(voucher_id, current_user.lender_id)
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

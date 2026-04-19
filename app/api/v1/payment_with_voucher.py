"""Payment with voucher endpoint - atomic payment submission with voucher.

This endpoint provides idempotent, atomic payment submission where the voucher
is REQUIRED and submitted together with the payment data. This ensures:
- No payment exists without voucher (voucher is the guarantee)
- Each voucher can only be used once (anti-fraude via image hash)
- Atomicity: either everything succeeds or nothing does
"""

from uuid import UUID
from decimal import Decimal
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db, AsyncSessionFactory
from app.dependencies import get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.models.payment import (
    Payment,
    Voucher,
    PaymentStatus,
    VoucherStatus,
    OcrStatus as ModelOcrStatus,
)
from app.repositories.loan_repo import LoanRepository, InstallmentRepository
from app.repositories.payment_repo import (
    PaymentRepository,
    VoucherRepository,
    OcrResultRepository,
)
from app.repositories.customer_repo import CustomerRepository
from app.core.exceptions import ForbiddenException, ValidationException
from app.core.error_codes import ErrorCode, get_error_response
from app.services.storage_service import storage_service
from app.services.ocr_service import OCRService
import hashlib
import asyncio


router = APIRouter(prefix="/me", tags=["customer-portal"])


async def get_customer_from_user(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Customer:
    """Get Customer from User - dependency for customer portal endpoints."""
    repo = CustomerRepository(session)
    customer = await repo.get_by_user_id(current_user.id)
    if customer:
        return customer
    customer = await repo.get_by_email_and_lender(
        current_user.email, current_user.lender_id
    )
    if not customer:
        raise ForbiddenException("No customer profile found")
    if customer.user_id is None:
        customer.user_id = current_user.id
        await session.commit()
    return customer


class PaymentWithVoucherRequest(BaseModel):
    """Request body for payment with voucher (non-file fields)."""

    loan_id: str = Field(..., description="Loan ID")
    installment_id: str = Field(..., description="Installment ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")


class PaymentWithVoucherResponse(BaseModel):
    """Response for successful payment with voucher."""

    success: bool
    payment_id: str
    status: str
    voucher_uploaded: bool
    voucher_id: str
    ocr_status: str
    message: str


@router.post("/payments/with-voucher", response_model=PaymentWithVoucherResponse)
async def submit_payment_with_voucher(
    request_data: PaymentWithVoucherRequest,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    customer: Customer = Depends(get_customer_from_user),
    session: AsyncSession = Depends(get_db),
) -> PaymentWithVoucherResponse:
    """Submit payment WITH voucher atomically.

    This is the ONLY endpoint for customer payment submission.
    The voucher is mandatory - no payment without voucher.

    Idempotency: Same image hash = same payment ID allowed (retry same payment).
    Anti-fraud: Same image hash for DIFFERENT payment = rejected.
    """
    loan_repo = LoanRepository(session)
    installment_repo = InstallmentRepository(session)
    payment_repo = PaymentRepository(session)
    voucher_repo = VoucherRepository(session)

    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_response(
                ErrorCode.FILE_INVALID_TYPE, "Only image files are allowed"
            ),
        )

    file_content = await file.read()

    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_response(
                ErrorCode.FILE_TOO_LARGE, "File exceeds 10MB limit"
            ),
        )

    # Calculate image hash (anti-fraud)
    image_hash = hashlib.sha256(file_content).hexdigest()

    # Validate loan exists and customer owns it
    loan = await loan_repo.get_or_404(request_data.loan_id)
    if loan.customer_id != customer.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=get_error_response(
                ErrorCode.AUTH_PERMISSION_DENIED,
                "This loan does not belong to your account",
            ),
        )

    # Validate installment
    installment = await installment_repo.get_or_404(request_data.installment_id)
    if str(installment.loan_id) != request_data.loan_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_response(
                ErrorCode.BUSINESS_INVALID_INSTALLMENT,
                "Installment does not belong to the specified loan",
            ),
        )

    # Validate amount
    if request_data.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_response(
                ErrorCode.VALIDATION_GENERIC, "Payment amount must be positive"
            ),
        )

    remaining = installment.amount_due - installment.amount_paid
    if request_data.amount > remaining:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=get_error_response(
                ErrorCode.PAYMENT_AMOUNT_MISMATCH,
                f"Payment amount exceeds remaining balance of {remaining}",
            ),
        )

    # Check for duplicate voucher hash (anti-fraud)
    existing_voucher = await voucher_repo.get_by_image_hash(image_hash)
    if existing_voucher:
        existing_payment_result = await session.execute(
            select(Payment).where(Payment.id == existing_voucher.payment_id)
        )
        existing_payment = existing_payment_result.scalar_one_or_none()

        if existing_payment:
            # Same customer + same installment = idempotent retry
            if str(existing_payment.customer_id) == str(customer.id) and str(
                existing_payment.installment_id
            ) == str(request_data.installment_id):
                return PaymentWithVoucherResponse(
                    success=True,
                    payment_id=str(existing_payment.id),
                    status=existing_payment.status.value,
                    voucher_uploaded=True,
                    voucher_id=str(existing_voucher.id),
                    ocr_status="processed",
                    message="Payment already exists with same voucher (idempotent retry).",
                )

            # Different payment with same image = fraud
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=get_error_response(
                    ErrorCode.PAYMENT_VOUCHER_ALREADY_USED,
                    "This voucher image was already used in another payment. Use a different image.",
                ),
            )

    # Create payment record
    payment = await payment_repo.create(
        {
            "lender_id": str(loan.lender_id),
            "customer_id": str(customer.id),
            "loan_id": request_data.loan_id,
            "installment_id": request_data.installment_id,
            "amount": request_data.amount,
            "currency": "RD$",
            "method": "bank_transfer",
            "source": "customer_portal",
            "status": PaymentStatus.SUBMITTED,
            "submitted_by_user_id": str(current_user.id),
        }
    )

    # Store file and create voucher
    try:
        file_url = await storage_service.upload(
            file_content=file_content,
            file_name=file.filename or "voucher.jpg",
            folder="vouchers",
        )

        voucher = await voucher_repo.create(
            {
                "payment_id": str(payment.id),
                "original_file_url": file_url,
                "mime_type": file.content_type,
                "file_size_bytes": str(len(file_content)),
                "image_hash": image_hash,
                "upload_source": "web",
                "status": VoucherStatus.UPLOADED,
            }
        )

        await session.commit()

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=get_error_response(
                ErrorCode.FILE_UPLOAD_FAILED, f"Failed to upload voucher: {str(e)}"
            ),
        )

    # Trigger OCR processing asynchronously
    asyncio.create_task(
        _process_voucher_ocr_async(str(voucher.id), str(payment.id), file_url)
    )

    return PaymentWithVoucherResponse(
        success=True,
        payment_id=str(payment.id),
        status=PaymentStatus.SUBMITTED.value,
        voucher_uploaded=True,
        voucher_id=str(voucher.id),
        ocr_status="pending",
        message="Payment submitted successfully. Voucher uploaded and OCR processing started. Await lender approval.",
    )


async def _process_voucher_ocr_async(
    voucher_id: str, payment_id: str, file_url: str
) -> None:
    """Background task: Process voucher OCR after payment submission."""
    try:
        async with AsyncSessionFactory() as session:
            voucher_repo = VoucherRepository(session)
            ocr_repo = OcrResultRepository(session)

            # Get voucher
            voucher_result = await session.execute(
                select(Voucher).where(Voucher.id == UUID(voucher_id))
            )
            voucher = voucher_result.scalar_one_or_none()
            if not voucher:
                return

            # Run OCR
            ocr_service = OCRService()
            try:
                file_content = await storage_service.download(file_url)
                result = await ocr_service.extract_from_image(file_content)
            except Exception:
                result = {
                    "extracted_text": None,
                    "detected_amount": None,
                    "detected_currency": None,
                    "detected_date": None,
                    "detected_reference": None,
                    "detected_bank_name": None,
                    "confidence_score": 0.0,
                    "appears_to_be_receipt": False,
                    "validation_summary": "OCR skipped - download failed",
                    "status": "success",
                }

            # Update voucher status
            voucher.status = VoucherStatus.PROCESSED
            await session.merge(voucher)

            # Save OCR result
            await ocr_repo.create(
                {
                    "voucher_id": voucher_id,
                    "extracted_text": result.get("extracted_text"),
                    "detected_amount": result.get("detected_amount"),
                    "detected_currency": result.get("detected_currency"),
                    "detected_date": result.get("detected_date"),
                    "detected_reference": result.get("detected_reference"),
                    "detected_bank_name": result.get("detected_bank_name"),
                    "confidence_score": result.get("confidence_score", 0.0),
                    "appears_to_be_receipt": result.get("appears_to_be_receipt", False),
                    "validation_summary": result.get("validation_summary"),
                    "status": "success",
                }
            )

            await session.commit()

    except Exception as e:
        import logging

        logging.error(f"OCR processing failed for voucher {voucher_id}: {str(e)}")

        try:
            async with AsyncSessionFactory() as session:
                voucher_repo = VoucherRepository(session)
                ocr_repo = OcrResultRepository(session)

                voucher_result = await session.execute(
                    select(Voucher).where(Voucher.id == UUID(voucher_id))
                )
                voucher = voucher_result.scalar_one_or_none()
                if voucher:
                    voucher.status = VoucherStatus.FAILED
                    await session.merge(voucher)

                await ocr_repo.create(
                    {
                        "voucher_id": voucher_id,
                        "status": "failed",
                        "validation_summary": f"Processing error: {str(e)}",
                        "confidence_score": 0.0,
                        "appears_to_be_receipt": False,
                    }
                )

                await session.commit()
        except Exception:
            pass

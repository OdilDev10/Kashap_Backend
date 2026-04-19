"""Voucher service - handle voucher uploads and OCR processing dispatch."""

import hashlib
import asyncio
from io import BytesIO
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image

from app.repositories.payment_repo import VoucherRepository, OcrResultRepository, PaymentMatchRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.loan_repo import InstallmentRepository
from app.models.payment import Voucher, VoucherStatus, OcrResult, PaymentMatch, Payment, OcrStatus
from app.core.exceptions import ValidationException, NotFoundException, ForbiddenException
from app.services.storage_service import storage_service
from app.services.ocr_service import OCRService


class VoucherService:
    """Service for voucher uploads and OCR processing."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.voucher_repo = VoucherRepository(session)
        self.ocr_repo = OcrResultRepository(session)
        self.match_repo = PaymentMatchRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.installment_repo = InstallmentRepository(session)
        self.ocr_service = OCRService()

    async def upload_voucher(
        self,
        payment_id: str,
        file_content: bytes,
        file_name: str,
        mime_type: str,
        upload_source: str,
        lender_id: str,
    ) -> dict:
        """Upload voucher image and dispatch OCR processing."""
        # Validate payment exists and user can upload
        payment = await self.payment_repo.get_or_404(payment_id)
        if str(payment.lender_id) != str(lender_id):
            raise ForbiddenException("Not authorized for this payment")

        # Validate file
        if not file_content:
            raise ValidationException("File content is empty")

        if len(file_content) > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationException("File size exceeds 10MB limit")

        # Validate mime type
        if mime_type not in ("image/jpeg", "image/png", "image/gif"):
            raise ValidationException(f"Unsupported file type: {mime_type}")

        # Calculate image hash (for duplicate detection)
        image_hash = hashlib.sha256(file_content).hexdigest()

        # Check for duplicates
        existing = await self.voucher_repo.get_by_image_hash(image_hash)
        if existing:
            if str(existing.payment_id) == str(payment_id):
                return {
                    "voucher_id": str(existing.id),
                    "payment_id": str(payment_id),
                    "status": existing.status.value if hasattr(existing.status, "value") else str(existing.status),
                    "message": "Voucher already exists for this payment",
                    "idempotent": True,
                }
            raise ValidationException("This voucher image has already been uploaded for another payment")

        # Store file
        file_url = await storage_service.upload(
            file_content=file_content,
            file_name=file_name,
            folder="vouchers",
        )

        # Create voucher record
        voucher = await self.voucher_repo.create({
            "payment_id": payment_id,
            "original_file_url": file_url,
            "mime_type": mime_type,
            "file_size_bytes": str(len(file_content)),
            "image_hash": image_hash,
            "upload_source": upload_source,
            "status": VoucherStatus.UPLOADED,
        })

        await self.session.commit()

        # Dispatch async OCR processing
        asyncio.create_task(self._process_voucher_ocr(voucher.id, file_url))

        return {
            "voucher_id": str(voucher.id),
            "payment_id": str(payment_id),
            "status": voucher.status.value,
            "message": "Voucher uploaded, processing started",
            "idempotent": False,
        }

    async def _process_voucher_ocr(self, voucher_id: str, file_url: str) -> None:
        """Background task: Extract text and data from voucher image."""
        try:
            # Get fresh session for background task
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                voucher_repo = VoucherRepository(session)
                payment_repo = PaymentRepository(session)
                ocr_repo = OcrResultRepository(session)

                voucher = await voucher_repo.get_or_404(voucher_id)
                payment = await payment_repo.get_or_404(voucher.payment_id)

                # Download and process image
                file_content = await storage_service.download(file_url)

                # Run OCR
                result = await self.ocr_service.extract_from_image(file_content)

                # Save OCR result
                ocr_result = await ocr_repo.create({
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
                    "status": result.get("status", OcrStatus.FAILED),
                })

                # Update voucher status
                voucher.status = VoucherStatus.PROCESSED
                await voucher_repo.update(voucher, {"status": VoucherStatus.PROCESSED})

                # Try to match with installment
                await self._match_payment_to_installment(
                    session,
                    payment=payment,
                    ocr_result=ocr_result,
                )

                await session.commit()

        except Exception as e:
            # Log error and mark voucher as failed
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                voucher_repo = VoucherRepository(session)
                ocr_repo = OcrResultRepository(session)
                voucher = await voucher_repo.get_or_404(voucher_id)
                voucher.status = VoucherStatus.FAILED
                await voucher_repo.update(voucher, {"status": VoucherStatus.FAILED})

                # Create failed OCR result
                await ocr_repo.create({
                    "voucher_id": voucher_id,
                    "status": OcrStatus.FAILED,
                    "validation_summary": f"Error: {str(e)}",
                    "confidence_score": 0.0,
                    "appears_to_be_receipt": False,
                })

                await session.commit()

    async def _match_payment_to_installment(
        self,
        session: AsyncSession,
        payment: Payment,
        ocr_result: OcrResult,
    ) -> None:
        """Match detected payment amount to installment due amount."""
        installment_repo = InstallmentRepository(session)
        match_repo = PaymentMatchRepository(session)
        installment = await installment_repo.get_or_404(payment.installment_id)

        # Compare amounts
        amount_matches = False
        if ocr_result.detected_amount:
            from decimal import Decimal
            detected = Decimal(str(ocr_result.detected_amount))
            due = installment.amount_due - installment.amount_paid
            # Allow 5% variance
            amount_matches = abs(detected - due) / due < Decimal("0.05")

        # Compare dates
        date_matches = bool(ocr_result.detected_date)

        # Create match record
        match_status = "matched" if (amount_matches and date_matches) else "needs_review"

        await match_repo.create({
            "payment_id": payment.id,
            "installment_id": payment.installment_id,
            "expected_amount": installment.amount_due - installment.amount_paid,
            "detected_amount": ocr_result.detected_amount,
            "amount_matches": amount_matches,
            "date_matches": date_matches,
            "reference_present": bool(ocr_result.detected_reference),
            "match_status": match_status,
        })

    async def get_voucher_details(self, voucher_id: str, lender_id: str) -> dict:
        """Get voucher details with OCR results."""
        voucher = await self.voucher_repo.get_or_404(voucher_id)
        payment = await self.payment_repo.get_or_404(voucher.payment_id)

        if str(payment.lender_id) != str(lender_id):
            raise ForbiddenException("Not authorized to view this voucher")

        ocr = await self.ocr_repo.get_by_voucher(voucher_id)
        match = await self.match_repo.get_for_installment(payment.installment_id) if payment.installment_id else None

        return {
            "voucher_id": str(voucher.id),
            "payment_id": str(payment.id),
            "file_url": voucher.original_file_url,
            "status": voucher.status.value,
            "ocr_result": {
                "extracted_text": ocr.extracted_text,
                "detected_amount": float(ocr.detected_amount) if ocr.detected_amount else None,
                "detected_currency": ocr.detected_currency,
                "detected_date": ocr.detected_date,
                "detected_bank": ocr.detected_bank_name,
                "confidence": float(ocr.confidence_score),
                "is_receipt": ocr.appears_to_be_receipt,
                "status": ocr.status.value,
            } if ocr else None,
            "match_result": {
                "expected_amount": float(match.expected_amount),
                "detected_amount": float(match.detected_amount) if match.detected_amount else None,
                "amount_matches": match.amount_matches,
                "date_matches": match.date_matches,
                "status": match.match_status,
            } if match else None,
            "uploaded_at": voucher.created_at.isoformat(),
        }

    async def list_vouchers_for_payment(self, payment_id: str, lender_id: str) -> dict:
        """List all vouchers for a payment."""
        payment = await self.payment_repo.get_or_404(payment_id)

        if str(payment.lender_id) != str(lender_id):
            raise ForbiddenException("Not authorized to view this payment")

        vouchers = await self.voucher_repo.get_by_payment(payment_id)

        return {
            "count": len(vouchers),
            "vouchers": [
                {
                    "voucher_id": str(v.id),
                    "status": v.status.value,
                    "file_size": int(v.file_size_bytes),
                    "uploaded_at": v.created_at.isoformat(),
                }
                for v in vouchers
            ],
        }

"""Payment schemas - request/response models."""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional


class OcrResultRead(BaseModel):
    """OCR extraction result."""
    detected_amount: Optional[Decimal]
    detected_currency: Optional[str]
    detected_date: Optional[str]
    detected_reference: Optional[str]
    detected_bank_name: Optional[str]
    confidence_score: float
    appears_to_be_receipt: bool
    status: str


class VoucherRead(BaseModel):
    """Voucher details."""
    voucher_id: str
    file_url: str
    status: str
    file_size_bytes: str
    upload_source: str
    ocr_result: Optional[OcrResultRead]
    created_at: datetime


class PaymentCreate(BaseModel):
    """Submit payment request."""
    loan_id: str
    installment_id: str
    amount: Decimal = Field(..., gt=0)


class PaymentApproveRequest(BaseModel):
    """Approve payment request."""
    review_notes: Optional[str] = None


class PaymentRejectRequest(BaseModel):
    """Reject payment request."""
    review_notes: str = Field(..., min_length=1)


class PaymentRead(BaseModel):
    """Payment details."""
    payment_id: str
    loan_id: str
    installment_id: Optional[str]
    customer_id: str
    amount: Decimal
    currency: str
    method: str
    status: str
    source: str
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    vouchers: list[VoucherRead]


class PaymentListItem(BaseModel):
    """Payment list item."""
    payment_id: str
    loan_id: str
    customer_id: str
    amount: Decimal
    status: str
    submitted_at: datetime


class VoucherUploadResponse(BaseModel):
    """Voucher upload response."""
    voucher_id: str
    payment_id: str
    status: str
    message: str

"""Payment models - customer payments and OCR results."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from enum import Enum

from sqlalchemy import (
    String,
    Numeric,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    Float,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.lender import Lender
    from app.models.customer import Customer
    from app.models.loan import Loan, Installment
    from app.models.user import User


class PaymentStatus(str, Enum):
    """Payment workflow states."""

    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaymentMethod(str, Enum):
    """Supported payment methods."""

    BANK_TRANSFER = "bank_transfer"


class PaymentSource(str, Enum):
    """Where payment originated."""

    CUSTOMER_PORTAL = "customer_portal"
    MANUAL_BACKOFFICE = "manual_backoffice"


class VoucherStatus(str, Enum):
    """Voucher processing states."""

    UPLOADED = "uploaded"
    PROCESSED = "processed"
    FAILED = "failed"


class OcrStatus(str, Enum):
    """OCR result states."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class Payment(Base, BaseModel):
    """Payment submitted by customer for loan installment."""

    __tablename__ = "payments"

    lender_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    loan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    installment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("installments.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Payment reference number
    payment_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )

    # Payment details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RD$", nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod),
        default=PaymentMethod.BANK_TRANSFER,
        nullable=False,
    )
    source: Mapped[PaymentSource] = mapped_column(
        SQLEnum(PaymentSource), nullable=False
    )

    # Workflow
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus),
        default=PaymentStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lender: Mapped[Lender] = relationship(foreign_keys=[lender_id])
    customer: Mapped[Customer] = relationship(foreign_keys=[customer_id])
    loan: Mapped[Loan] = relationship(back_populates="payments", foreign_keys=[loan_id])
    installment: Mapped[Optional[Installment]] = relationship(
        back_populates="payments", foreign_keys=[installment_id]
    )
    submitted_by_user: Mapped[User] = relationship(foreign_keys=[submitted_by_user_id])
    reviewed_by_user: Mapped[Optional[User]] = relationship(
        foreign_keys=[reviewed_by_user_id]
    )
    vouchers: Mapped[list[Voucher]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )
    matches: Mapped[list[PaymentMatch]] = relationship(
        back_populates="payment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Payment {self.id}>"


class Voucher(Base, BaseModel):
    """Bank transfer receipt/voucher for payment validation."""

    __tablename__ = "vouchers"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # File details
    original_file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    processed_file_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )
    mime_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[str] = mapped_column(String(20), nullable=False)
    image_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True
    )

    # Metadata
    upload_source: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # mobile, web
    status: Mapped[VoucherStatus] = mapped_column(
        SQLEnum(VoucherStatus),
        default=VoucherStatus.UPLOADED,
        nullable=False,
        index=True,
    )

    # Relationships
    payment: Mapped[Payment] = relationship(
        back_populates="vouchers", foreign_keys=[payment_id]
    )
    ocr_result: Mapped[Optional[OcrResult]] = relationship(
        back_populates="voucher",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Voucher {self.id}>"


class OcrResult(Base, BaseModel):
    """OCR extraction result from voucher image."""

    __tablename__ = "ocr_results"

    voucher_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("vouchers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )

    # Extracted data
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    detected_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    detected_date: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # Flexible date format
    detected_reference: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    detected_bank_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )

    # Confidence
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0-1.0
    appears_to_be_receipt: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Validation summary
    validation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[OcrStatus] = mapped_column(
        SQLEnum(OcrStatus),
        default=OcrStatus.FAILED,
        nullable=False,
        index=True,
    )

    # Relationships
    voucher: Mapped[Voucher] = relationship(
        back_populates="ocr_result", foreign_keys=[voucher_id]
    )

    def __repr__(self) -> str:
        return f"<OcrResult {self.id}>"


class PaymentMatch(Base, BaseModel):
    """Matching result between payment and installment via OCR."""

    __tablename__ = "payment_matches"

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    installment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("installments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Comparison details
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    detected_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    amount_matches: Mapped[bool] = mapped_column(Boolean, nullable=False)
    date_matches: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reference_present: Mapped[bool] = mapped_column(Boolean, nullable=False)
    match_status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # matched, mismatch, needs_review

    # Relationships
    payment: Mapped[Payment] = relationship(
        back_populates="matches", foreign_keys=[payment_id]
    )
    installment: Mapped[Installment] = relationship(foreign_keys=[installment_id])

    def __repr__(self) -> str:
        return f"<PaymentMatch {self.id}>"

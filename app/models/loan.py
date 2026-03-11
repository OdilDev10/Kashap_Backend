"""Loan models - approved loan instances and installments."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from enum import Enum

from sqlalchemy import String, Numeric, Integer, Date, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.lender import Lender
    from app.models.customer import Customer
    from app.models.loan_application import LoanApplication
    from app.models.user import User
    from app.models.lender import LenderBankAccount
    from app.models.payment import Payment


class LoanStatus(str, Enum):
    """Loan lifecycle states."""
    APPROVED = "approved"
    DISBURSED = "disbursed"
    ACTIVE = "active"
    OVERDUE = "overdue"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InstallmentStatus(str, Enum):
    """Installment payment states."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    REJECTED = "rejected"


class DisbursementStatus(str, Enum):
    """Disbursement execution states."""
    PENDING = "pending"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Loan(Base, BaseModel):
    """Approved loan from customer's application."""

    __tablename__ = "loans"

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
    loan_application_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Loan details
    loan_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    principal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    interest_type: Mapped[str] = mapped_column(String(20), default="fixed", nullable=False)
    total_interest_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Installment plan
    installments_count: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    disbursement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    first_due_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    status: Mapped[LoanStatus] = mapped_column(
        SQLEnum(LoanStatus),
        default=LoanStatus.APPROVED,
        nullable=False,
        index=True,
    )
    approved_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lender: Mapped[Lender] = relationship(foreign_keys=[lender_id])
    customer: Mapped[Customer] = relationship(foreign_keys=[customer_id])
    application: Mapped[LoanApplication] = relationship(foreign_keys=[loan_application_id])
    approved_by_user: Mapped[User] = relationship(foreign_keys=[approved_by])
    installments: Mapped[list[Installment]] = relationship(back_populates="loan", cascade="all, delete-orphan")
    disbursements: Mapped[list[Disbursement]] = relationship(back_populates="loan", cascade="all, delete-orphan")
    payments: Mapped[list[Payment]] = relationship(back_populates="loan")

    def __repr__(self) -> str:
        return f"<Loan {self.loan_number}>"


class Disbursement(Base, BaseModel):
    """Loan disbursement to customer."""

    __tablename__ = "disbursements"

    loan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lender_bank_account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lender_bank_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Disbursement details
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)  # bank_transfer, cash, other
    bank_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    receipt_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[DisbursementStatus] = mapped_column(
        SQLEnum(DisbursementStatus),
        default=DisbursementStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    disbursed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    loan: Mapped[Loan] = relationship(back_populates="disbursements", foreign_keys=[loan_id])
    bank_account: Mapped[Optional[LenderBankAccount]] = relationship(foreign_keys=[lender_bank_account_id])
    created_by_user: Mapped[User] = relationship(foreign_keys=[created_by])

    def __repr__(self) -> str:
        return f"<Disbursement {self.id}>"


class Installment(Base, BaseModel):
    """Loan installment - individual payment due."""

    __tablename__ = "installments"

    loan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("loans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Installment sequence
    installment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Amount breakdown
    principal_component: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    interest_component: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    late_fee_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    # Status
    status: Mapped[InstallmentStatus] = mapped_column(
        SQLEnum(InstallmentStatus),
        default=InstallmentStatus.PENDING,
        nullable=False,
        index=True,
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    loan: Mapped[Loan] = relationship(back_populates="installments", foreign_keys=[loan_id])
    payments: Mapped[list[Payment]] = relationship(back_populates="installment")

    @property
    def is_overdue(self) -> bool:
        """Check if installment is overdue."""
        return date.today() > self.due_date and self.status in (
            InstallmentStatus.PENDING,
            InstallmentStatus.PARTIAL
        )

    def __repr__(self) -> str:
        return f"<Installment {self.installment_number}>"

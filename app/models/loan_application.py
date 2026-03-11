"""Loan Application model - customer requests for loans."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from enum import Enum

from sqlalchemy import String, Numeric, Integer, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.lender import Lender
    from app.models.customer import Customer
    from app.models.user import User


class LoanApplicationStatus(str, Enum):
    """Loan application lifecycle states."""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class LoanFrequency(str, Enum):
    """Payment frequency options."""
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class LoanApplication(Base, BaseModel):
    """Loan application submitted by customer."""

    __tablename__ = "loan_applications"

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

    # Requested terms
    requested_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    requested_interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    requested_installments_count: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    purpose: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Review
    status: Mapped[LoanApplicationStatus] = mapped_column(
        SQLEnum(LoanApplicationStatus),
        default=LoanApplicationStatus.SUBMITTED,
        nullable=False,
        index=True,
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    lender: Mapped[Lender] = relationship(foreign_keys=[lender_id])
    customer: Mapped[Customer] = relationship(foreign_keys=[customer_id])
    reviewer: Mapped[Optional[User]] = relationship(foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<LoanApplication {self.id}>"

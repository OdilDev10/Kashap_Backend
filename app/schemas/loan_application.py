"""Loan application schemas - request/response models."""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional


class LoanApplicationCreate(BaseModel):
    """Create loan application request."""
    requested_amount: Decimal = Field(..., gt=0)
    requested_interest_rate: Decimal = Field(..., ge=0)
    requested_installments_count: int = Field(..., gt=0)
    requested_frequency: str = Field(..., regex="^(weekly|biweekly|monthly)$")
    purpose: Optional[str] = None


class LoanApplicationRead(BaseModel):
    """Loan application response."""
    application_id: str
    customer_id: str
    requested_amount: Decimal
    requested_interest_rate: Decimal
    requested_installments_count: int
    requested_frequency: str
    purpose: Optional[str]
    status: str
    reviewed_by: Optional[str]
    reviewed_at: Optional[datetime]
    review_notes: Optional[str]
    created_at: datetime


class LoanApplicationReviewRequest(BaseModel):
    """Review loan application request."""
    review_notes: str = Field(..., min_length=1)


class LoanApplicationApproveRequest(BaseModel):
    """Approve loan application request."""
    review_notes: Optional[str] = None


class LoanApplicationListItem(BaseModel):
    """Loan application list item."""
    application_id: str
    customer_id: str
    requested_amount: Decimal
    status: str
    created_at: datetime

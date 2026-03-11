"""Loan schemas - request/response models."""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import date, datetime
from typing import Optional


class InstallmentRead(BaseModel):
    """Installment details."""
    number: int
    due_date: date
    principal_component: Decimal
    interest_component: Decimal
    amount_due: Decimal
    amount_paid: Decimal
    late_fee_amount: Decimal
    status: str
    paid_at: Optional[datetime]


class LoanCreate(BaseModel):
    """Create loan from application."""
    application_id: str
    first_due_date: date
    internal_notes: Optional[str] = None


class LoanRead(BaseModel):
    """Loan response."""
    loan_id: str
    loan_number: str
    principal_amount: Decimal
    interest_rate: Decimal
    total_interest_amount: Decimal
    total_amount: Decimal
    installments_count: int
    frequency: str
    status: str
    first_due_date: date
    disbursement_date: Optional[date]
    approved_at: datetime
    installments: list[InstallmentRead]
    created_at: datetime


class LoanListItem(BaseModel):
    """Loan list item."""
    loan_id: str
    loan_number: str
    principal_amount: Decimal
    status: str
    created_at: datetime


class DisbursementCreate(BaseModel):
    """Create disbursement request."""
    amount: Decimal = Field(..., gt=0)
    method: str
    bank_name: Optional[str] = None
    reference_number: Optional[str] = None
    receipt_url: Optional[str] = None


class DisbursementRead(BaseModel):
    """Disbursement details."""
    disbursement_id: str
    loan_id: str
    amount: Decimal
    method: str
    bank_name: Optional[str]
    reference_number: Optional[str]
    status: str
    disbursed_at: Optional[datetime]

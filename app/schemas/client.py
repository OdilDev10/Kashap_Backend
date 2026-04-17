"""Client portal schemas - loan products and applications."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoanProductLender(BaseModel):
    """Lender info for loan product."""

    id: str
    name: str
    type: str
    logo_url: Optional[str] = None


class LoanProductItem(BaseModel):
    """Loan product item."""

    id: str
    lender: LoanProductLender
    name: str
    description: str
    min_amount: float
    max_amount: float
    min_installments: int
    max_installments: int
    annual_interest_rate: float
    example_amount: float
    example_monthly_payment: float
    is_featured: bool


class LoanProductFilters(BaseModel):
    """Available filters for loan products."""

    institutions: list[dict]  # {id, name}
    amount_ranges: list[dict]  # {min, max}
    installment_ranges: list[dict]  # {min, max}


class PaginatedLoanProductsResponse(BaseModel):
    """Paginated loan products response."""

    items: list[LoanProductItem]
    total: int
    skip: int
    limit: int


# Applications
class ClientApplicationItem(BaseModel):
    """Client application item."""

    id: str
    loan_product_id: str
    lender_name: str
    loan_name: str
    amount: float
    installments: int
    annual_interest_rate: float
    status: str  # pending, in_review, approved, rejected
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class PaginatedApplicationsResponse(BaseModel):
    """Paginated applications response."""

    items: list[ClientApplicationItem]
    total: int
    skip: int
    limit: int


# My Loans / Payments
class ActiveLoanInfo(BaseModel):
    """Active loan info."""

    id: str
    loan_product_name: str
    lender_name: str
    amount: float
    installments_count: int
    installment_amount: float


class PaymentKPIs(BaseModel):
    """Payment KPIs."""

    next_payment_amount: float
    next_payment_due_date: str
    total_paid: float
    completed_installments: int
    remaining_balance: float
    remaining_installments: int


class ScheduleItem(BaseModel):
    """Payment schedule item."""

    installment_number: int
    due_date: str
    amount: float
    status: str  # paid, pending, next, overdue
    paid_at: Optional[str] = None
    voucher_url: Optional[str] = None


class ClientPaymentScheduleResponse(BaseModel):
    """Client payment schedule response."""

    active_loan: ActiveLoanInfo
    kpis: PaymentKPIs
    payment_schedule: list[ScheduleItem]

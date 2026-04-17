"""Dashboard and reports schemas - lender stats, KPIs, collections."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class CollectionWeekItem(BaseModel):
    """Single week collection data."""

    week: int
    amount: float


class LoanStatusBreakdown(BaseModel):
    """Loan status breakdown."""

    count: int
    percentage: float


class LoanStatusDistribution(BaseModel):
    """Loan status distribution."""

    on_time: LoanStatusBreakdown
    delayed: LoanStatusBreakdown
    overdue: LoanStatusBreakdown


class RecentActivityItem(BaseModel):
    """Recent activity item."""

    id: str
    type: str  # payment, loan_created, overdue_alert, voucher_pending
    client_name: str
    description: str
    amount: float
    time_ago: str
    loan_id: Optional[str] = None


class LenderDashboardKPIs(BaseModel):
    """Dashboard KPI values."""

    active_loans: int
    active_loans_change: int
    total_disbursed: float
    collected_this_month: float
    collected_this_month_change: float
    overdue_count: int
    overdue_amount: float


class LenderDashboardResponse(BaseModel):
    """Full lender dashboard response."""

    kpis: LenderDashboardKPIs
    collections_chart: list[CollectionWeekItem]
    loan_status: LoanStatusDistribution
    recovery_rate: float
    avg_days_overdue: int
    default_rate: float
    recent_activity: list[RecentActivityItem]


# Loans
class LoanProgress(BaseModel):
    """Loan repayment progress."""

    current: int
    total: int


class LoanListItem(BaseModel):
    """Loan item for list view."""

    id: str
    loan_number: str
    client_name: str
    client_document: str
    principal_amount: float
    installment_amount: float
    progress: LoanProgress
    status: str
    created_at: datetime


class LoanKPIs(BaseModel):
    """Loan screen KPIs."""

    total_loans: int
    active_loans: int
    pending_loans: int
    completed_loans: int


class PaginatedLoansResponse(BaseModel):
    """Paginated loans response."""

    items: list[LoanListItem]
    total: int
    skip: int
    limit: int


# Customers
class CustomerListItem(BaseModel):
    """Customer item for list view."""

    id: str
    full_name: str
    email: str
    phone: str
    document_type: str
    document_number: str
    active_loans_count: int
    status: str  # current, delayed, overdue
    created_at: datetime


class PaginatedCustomersResponse(BaseModel):
    """Paginated customers response."""

    items: list[CustomerListItem]
    total: int
    skip: int
    limit: int


# Payments
class PendingVoucherItem(BaseModel):
    """Pending voucher for review."""

    id: str
    client_name: str
    loan_id: str
    loan_number: str
    installment_number: int
    amount: float
    ocr_confidence: float
    voucher_image_url: str
    submitted_at: datetime


class PaymentKPIs(BaseModel):
    """Payment screen KPIs."""

    pending_count: int
    approved_today: int
    rejected_count: int
    total_this_month: float


class PaginatedPaymentsResponse(BaseModel):
    """Paginated payments response."""

    items: list[PendingVoucherItem]
    total: int
    skip: int
    limit: int


# Users / Team
class RoleItem(BaseModel):
    """Role item."""

    id: str
    name: str
    description: str
    permissions_count: int


class UserItem(BaseModel):
    """User item for list view."""

    id: str
    first_name: str
    last_name: str
    email: str
    role: str
    status: str  # active, inactive
    created_at: datetime


class PaginatedUsersResponse(BaseModel):
    """Paginated users response."""

    items: list[UserItem]
    total: int
    skip: int
    limit: int


# Settings
class CompanyInfo(BaseModel):
    """Company information."""

    legal_name: str
    trade_name: Optional[str]
    rnc: str
    email: str
    phone: str
    address: Optional[str]


class SubscriptionInfo(BaseModel):
    """Subscription information."""

    plan: str
    price: float
    billing_cycle: str  # monthly, yearly
    renewal_date: Optional[datetime]
    status: str  # active, expired, cancelled


class LenderSettingsResponse(BaseModel):
    """Lender settings response."""

    company: CompanyInfo
    subscription: SubscriptionInfo

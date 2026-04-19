"""Admin schemas - platform admin lender management."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AdminLenderCard(BaseModel):
    """Lender card for admin list."""

    id: str
    legal_name: str
    commercial_name: Optional[str]
    lender_type: str  # financiera, prestamista, cooperativa
    document_type: str  # RNC, Cédula
    document_number: str
    status: str  # active, in_review, suspended
    plan: str  # basic, professional, enterprise
    clients_count: int
    loans_count: int
    portfolio_amount: float
    registered_at: datetime
    reviewed_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None


class AdminLenderKPIs(BaseModel):
    """Admin dashboard KPIs."""

    total_entities: int
    active_count: int
    in_review_count: int
    suspended_count: int


class PaginatedAdminLendersResponse(BaseModel):
    """Paginated admin lenders response."""

    items: list[AdminLenderCard]
    total: int
    skip: int
    limit: int


class PlanFeatures(BaseModel):
    """Features included in a plan."""

    max_clients: int
    max_loans: int
    max_users: int
    ocr_validation: bool
    api_access: bool
    priority_support: bool


class PlanDetails(BaseModel):
    """Plan details for admin view."""

    plan_id: str
    name: str
    description: str
    price_monthly: float
    currency: str = "USD"
    features: PlanFeatures
    is_active: bool = True


class PlanStats(BaseModel):
    """Plan usage statistics."""

    plan_id: str
    plan_name: str
    active_subscriptions: int
    trial_subscriptions: int
    total_revenue: float
    avg_loan_amount: float


class AdminPlansResponse(BaseModel):
    """Response with all plans and their statistics."""

    plans: list[PlanDetails]
    stats: list[PlanStats]
    total_lenders: int
    total_active_lenders: int

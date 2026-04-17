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

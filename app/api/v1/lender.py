"""Lender dashboard API - dashboard stats, loans, customers, payments, users."""

from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_lender_context, require_roles
from app.models.user import User
from app.schemas.dashboard import (
    LenderDashboardResponse,
    PaginatedLoansResponse,
    PaginatedCustomersResponse,
    PaginatedPaymentsResponse,
    LoanKPIs,
    PaymentKPIs,
)
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/lender", tags=["lender"])


@router.get("/dashboard", response_model=LenderDashboardResponse)
async def get_lender_dashboard(
    current_user: User = Depends(
        require_roles("owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> LenderDashboardResponse:
    """Get full dashboard with KPIs, charts, and recent activity."""
    service = DashboardService(session)
    data = await service.get_lender_dashboard(lender_id)
    return LenderDashboardResponse(**data)


@router.get("/loans")
async def list_lender_loans(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaginatedLoansResponse:
    """List loans for lender with pagination and search."""
    service = DashboardService(session)
    items, total = await service.list_loans(lender_id, search, status, skip, limit)
    return PaginatedLoansResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/loans/kpis")
async def get_loan_kpis(
    current_user: User = Depends(
        require_roles("owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> LoanKPIs:
    """Get loan screen KPIs."""
    service = DashboardService(session)
    data = await service.get_loan_kpis(lender_id)
    return LoanKPIs(**data)


@router.get("/customers")
async def list_lender_customers(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_roles("owner", "manager", "reviewer", "agent")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaginatedCustomersResponse:
    """List customers for lender with pagination and search."""
    service = DashboardService(session)
    items, total = await service.list_customers(lender_id, search, status, skip, limit)
    return PaginatedCustomersResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/payments")
async def list_lender_payments(
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles("owner", "manager", "reviewer")),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaginatedPaymentsResponse:
    """List pending payment vouchers for lender with pagination and search."""
    service = DashboardService(session)
    items, total = await service.list_pending_vouchers(lender_id, search, skip, limit)
    return PaginatedPaymentsResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/payments/kpis")
async def get_payment_kpis(
    current_user: User = Depends(require_roles("owner", "manager", "reviewer")),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> PaymentKPIs:
    """Get payment screen KPIs."""
    service = DashboardService(session)
    data = await service.get_payment_kpis(lender_id)
    return PaymentKPIs(**data)

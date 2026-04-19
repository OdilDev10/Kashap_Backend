"""Admin System API - Platform system health and configuration."""

from datetime import datetime
from platform import python_version, system
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.models.lender import Lender
from app.models.customer import Customer
from app.models.loan import Loan
from app.models.payment import Payment


router = APIRouter(prefix="/admin/system", tags=["admin-system"])


@router.get("/health")
async def get_system_health(
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get platform system health status."""

    db_healthy = True
    try:
        await session.execute(select(1))
    except Exception:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": "development",
        "version": "0.1.0",
    }


@router.get("/stats")
async def get_platform_stats(
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get platform statistics."""

    total_lenders = await session.execute(select(func.count(Lender.id)))
    lenders_count = total_lenders.scalar() or 0

    total_customers = await session.execute(select(func.count(Customer.id)))
    customers_count = total_customers.scalar() or 0

    total_loans = await session.execute(select(func.count(Loan.id)))
    loans_count = total_loans.scalar() or 0

    total_payments = await session.execute(select(func.count(Payment.id)))
    payments_count = total_payments.scalar() or 0

    return {
        "total_lenders": lenders_count,
        "total_customers": customers_count,
        "total_loans": loans_count,
        "total_payments": payments_count,
        "python_version": python_version(),
        "platform": system(),
    }


@router.get("/config")
async def get_platform_config(
    _: User = Depends(require_roles("platform_admin")),
) -> dict:
    """Get platform configuration (non-sensitive)."""

    return {
        "platform_name": "OptiCredit",
        "api_version": "0.1.0",
        "environment": "development",
        "features": {
            "ocr_enabled": True,
            "braintree_enabled": False,
            "email_enabled": False,
            "sms_enabled": False,
        },
        "limits": {
            "max_file_size_mb": 10,
            "allowed_file_types": ["jpg", "jpeg", "png", "pdf"],
            "api_rate_limit": 100,
        },
    }


@router.get("/audit-log")
async def get_audit_log(
    _: User = Depends(require_roles("platform_admin")),
) -> dict:
    """Get recent audit log entries (mock)."""

    return {
        "entries": [
            {
                "id": "1",
                "action": "lender_approved",
                "user": "admin@opticredit.com",
                "target": "Financiera ABC",
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "id": "2",
                "action": "plan_updated",
                "user": "admin@opticredit.com",
                "target": "Plan Profesional",
                "timestamp": datetime.utcnow().isoformat(),
            },
            {
                "id": "3",
                "action": "lender_suspended",
                "user": "admin@opticredit.com",
                "target": "Prestamista XYZ",
                "timestamp": datetime.utcnow().isoformat(),
            },
        ],
        "total": 3,
    }

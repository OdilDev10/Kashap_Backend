"""Admin Plans API - SaaS plan management for platform admin."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.models.lender import Lender
from app.schemas.admin import (
    AdminPlansResponse,
    PlanDetails,
    PlanFeatures,
    PlanStats,
)


router = APIRouter(prefix="/admin/plans", tags=["admin-plans"])


PLANS_DATA = {
    "basic": {
        "plan_id": "basic",
        "name": "Básico",
        "description": "Para pequeñas financieras que inician. Incluye funcionalidades esenciales.",
        "price_monthly": 49.0,
        "features": {
            "max_clients": 100,
            "max_loans": 50,
            "max_users": 3,
            "ocr_validation": False,
            "api_access": False,
            "priority_support": False,
        },
    },
    "professional": {
        "plan_id": "professional",
        "name": "Profesional",
        "description": "Para financieras en crecimiento. OCR avanzado y más capacidad.",
        "price_monthly": 149.0,
        "features": {
            "max_clients": 500,
            "max_loans": 250,
            "max_users": 10,
            "ocr_validation": True,
            "api_access": False,
            "priority_support": False,
        },
    },
    "enterprise": {
        "plan_id": "enterprise",
        "name": "Empresarial",
        "description": "Solución completa para grandes operaciones. API, soporte prioritario y sin límites.",
        "price_monthly": 499.0,
        "features": {
            "max_clients": -1,
            "max_loans": -1,
            "max_users": -1,
            "ocr_validation": True,
            "api_access": True,
            "priority_support": True,
        },
    },
}


@router.get("", response_model=AdminPlansResponse)
async def get_plans_admin(
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> AdminPlansResponse:
    """Get all plans with usage statistics."""

    plans = []
    stats = []

    for plan_data in PLANS_DATA.values():
        features = PlanFeatures(**plan_data["features"])
        plan = PlanDetails(
            plan_id=plan_data["plan_id"],
            name=plan_data["name"],
            description=plan_data["description"],
            price_monthly=plan_data["price_monthly"],
            features=features,
        )
        plans.append(plan)

    for plan_id, plan_data in PLANS_DATA.items():
        query = select(func.count(Lender.id)).where(Lender.subscription_plan == plan_id)
        result = await session.execute(query)
        active_count = result.scalar() or 0

        trial_query = select(func.count(Lender.id)).where(
            Lender.subscription_plan == plan_id
        )
        trial_result = await session.execute(trial_query)
        trial_count = trial_result.scalar() or 0

        revenue_query = select(func.count(Lender.id)).where(
            Lender.subscription_plan == plan_id
        )
        revenue_result = await session.execute(revenue_query)
        revenue = float(revenue_result.scalar() or 0) * plan_data["price_monthly"]

        avg = 0.0

        plan_stat = PlanStats(
            plan_id=plan_id,
            plan_name=plan_data["name"],
            active_subscriptions=active_count,
            trial_subscriptions=trial_count,
            total_revenue=revenue,
            avg_loan_amount=avg,
        )
        stats.append(plan_stat)

    total_query = select(func.count(Lender.id))
    total_result = await session.execute(total_query)
    total_lenders = total_result.scalar() or 0

    active_query = select(func.count(Lender.id))
    active_result = await session.execute(active_query)
    total_active = active_result.scalar() or 0

    return AdminPlansResponse(
        plans=plans,
        stats=stats,
        total_lenders=total_lenders,
        total_active_lenders=total_active,
    )

"""Admin Users API - Platform user management with pagination and search."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User
from app.models.lender import Lender
from app.repositories.user_repo import UserRepository
from app.core.enums import UserStatus


router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _serialize_user_card(user: User, lender_name: str | None) -> dict:
    """Serialize user row for admin responses."""
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "account_type": user.account_type.value
        if hasattr(user.account_type, "value")
        else str(user.account_type),
        "status": user.status.value if hasattr(user.status, "value") else str(user.status),
        "lender_id": str(user.lender_id) if user.lender_id else None,
        "lender_name": lender_name,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        # Optional audit fields (may not exist in current schema yet).
        "disabled_at": (
            user.disabled_at.isoformat()
            if getattr(user, "disabled_at", None)
            else None
        ),
        "disabled_by": (
            str(getattr(user, "disabled_by")) if getattr(user, "disabled_by", None) else None
        ),
        "enabled_at": (
            user.enabled_at.isoformat()
            if getattr(user, "enabled_at", None)
            else None
        ),
        "enabled_by": (
            str(getattr(user, "enabled_by")) if getattr(user, "enabled_by", None) else None
        ),
    }


@router.get("")
async def list_admin_users(
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """List all users for admin with pagination and search."""
    repo = UserRepository(session)
    query = select(User)
    count_query = select(func.count(User.id))

    if search:
        search_filter = or_(
            User.email.ilike(f"%{search}%"),
            User.first_name.ilike(f"%{search}%"),
            User.last_name.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)

    if status:
        query = query.where(User.status == status)
        count_query = count_query.where(User.status == status)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(User.created_at)).offset(skip).limit(limit)
    result = await session.execute(query)
    users = result.scalars().all()

    items = []
    for user in users:
        lender_name = None
        if user.lender_id:
            lender_result = await session.execute(
                select(Lender.legal_name).where(Lender.id == str(user.lender_id))
            )
            lender_name = lender_result.scalar_one_or_none()

        items.append(_serialize_user_card(user, lender_name))

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/kpis")
async def get_admin_user_kpis(
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get admin dashboard KPIs for users."""
    total_result = await session.execute(select(func.count(User.id)))
    total = total_result.scalar() or 0

    active_result = await session.execute(
        select(func.count(User.id)).where(User.status == "active")
    )
    active = active_result.scalar() or 0

    inactive_result = await session.execute(
        select(func.count(User.id)).where(User.status == "inactive")
    )
    inactive = inactive_result.scalar() or 0

    blocked_result = await session.execute(
        select(func.count(User.id)).where(User.status == "blocked")
    )
    blocked = blocked_result.scalar() or 0

    platform_admins_result = await session.execute(
        select(func.count(User.id)).where(User.role == "platform_admin")
    )
    platform_admins = platform_admins_result.scalar() or 0

    return {
        "total_users": total,
        "active_users": active,
        "inactive_users": inactive,
        "platform_admins": platform_admins,
    }


@router.patch("/{user_id}/disable", status_code=status.HTTP_200_OK)
async def disable_user(
    user_id: str,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Disable a user account (set status to blocked)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.status = UserStatus.BLOCKED
    session.add(user)
    await session.commit()
    await session.refresh(user)

    lender_name = None
    if user.lender_id:
        lender_result = await session.execute(
            select(Lender.legal_name).where(Lender.id == str(user.lender_id))
        )
        lender_name = lender_result.scalar_one_or_none()

    return {
        "success": True,
        "message": "User disabled successfully",
        "user": _serialize_user_card(user, lender_name),
    }


@router.patch("/{user_id}/enable", status_code=status.HTTP_200_OK)
async def enable_user(
    user_id: str,
    _: User = Depends(require_roles("platform_admin")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Enable a user account (set status to active)."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.status = UserStatus.ACTIVE
    session.add(user)
    await session.commit()
    await session.refresh(user)

    lender_name = None
    if user.lender_id:
        lender_result = await session.execute(
            select(Lender.legal_name).where(Lender.id == str(user.lender_id))
        )
        lender_name = lender_result.scalar_one_or_none()

    return {
        "success": True,
        "message": "User enabled successfully",
        "user": _serialize_user_card(user, lender_name),
    }

"""Audit logs API for tenant-scoped activity logging."""

from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_lender_context, require_roles
from app.models.user import User
from app.repositories.audit_log_repo import AuditLogRepository


router = APIRouter(prefix="/lender", tags=["lender"])


class AuditLogItem(BaseModel):
    """Single audit log entry."""

    id: str
    user_id: str | None
    user_email: str | None
    user_name: str | None
    action: str
    resource_type: str
    resource_id: str | None
    description: str | None
    ip_address: str | None
    created_at: datetime


class AuditLogsResponse(BaseModel):
    """Paginated audit logs response."""

    items: list[AuditLogItem]
    total: int
    skip: int
    limit: int


@router.get("/audit-logs", response_model=AuditLogsResponse)
async def list_audit_logs(
    search: str | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(
        require_roles("platform_admin", "owner", "manager", "reviewer")
    ),
    lender_id: str = Depends(get_lender_context),
    session: AsyncSession = Depends(get_db),
) -> AuditLogsResponse:
    """List audit logs for the lender with filters and pagination."""
    repo = AuditLogRepository(session)

    user_uuid: UUID | None = None
    if user_id:
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            pass

    items, total = await repo.list_by_lender(
        lender_id=UUID(lender_id),
        user_id=user_uuid,
        action=action,
        resource_type=resource_type,
        search=search,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )

    return AuditLogsResponse(
        items=[
            AuditLogItem(
                id=str(log.id),
                user_id=str(log.user_id) if log.user_id else None,
                user_email=log.user_email,
                user_name=log.user_name,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                description=log.description,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in items
        ],
        total=total,
        skip=skip,
        limit=limit,
    )

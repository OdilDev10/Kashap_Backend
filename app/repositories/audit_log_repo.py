"""Audit log repository for querying audit records."""

from typing import Tuple, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc

from app.repositories.base import BaseRepository
from app.models.audit_log import AuditLog


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for audit log queries."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLog)

    async def list_by_lender(
        self,
        lender_id: UUID,
        user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[list[AuditLog], int]:
        """List audit logs with filters."""
        conditions = [
            self.model.lender_id == lender_id,
        ]

        if user_id:
            conditions.append(self.model.user_id == user_id)

        if action:
            conditions.append(self.model.action == action)

        if resource_type:
            conditions.append(self.model.resource_type == resource_type)

        if resource_id:
            conditions.append(self.model.resource_id == resource_id)

        if date_from:
            conditions.append(self.model.created_at >= date_from)

        if date_to:
            conditions.append(self.model.created_at <= date_to)

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    self.model.description.ilike(search_pattern),
                    self.model.user_email.ilike(search_pattern),
                    self.model.user_name.ilike(search_pattern),
                    self.model.resource_id.ilike(search_pattern),
                )
            )

        # Count query
        count_stmt = select(func.count(self.model.id)).where(and_(*conditions))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Data query
        query = (
            select(self.model)
            .where(and_(*conditions))
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_by_resource(
        self,
        lender_id: UUID,
        resource_type: str,
        resource_id: str,
        limit: int = 20,
    ) -> list[AuditLog]:
        """Get audit logs for a specific resource."""
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.lender_id == lender_id,
                    self.model.resource_type == resource_type,
                    self.model.resource_id == resource_id,
                )
            )
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_user(
        self,
        lender_id: UUID,
        user_id: UUID,
        limit: int = 50,
    ) -> list[AuditLog]:
        """Get audit logs for a specific user."""
        query = (
            select(self.model)
            .where(
                and_(
                    self.model.lender_id == lender_id,
                    self.model.user_id == user_id,
                )
            )
            .order_by(desc(self.model.created_at))
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_for_platform(
        self,
        user_id: UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[list[AuditLog], int]:
        """List audit logs for platform-wide queries (admin)."""
        conditions = []

        if user_id:
            conditions.append(self.model.user_id == user_id)

        if action:
            conditions.append(self.model.action == action)

        if resource_type:
            conditions.append(self.model.resource_type == resource_type)

        if resource_id:
            conditions.append(self.model.resource_id == resource_id)

        if search:
            search_pattern = f"%{search}%"
            conditions.append(
                or_(
                    self.model.description.ilike(search_pattern),
                    self.model.user_email.ilike(search_pattern),
                    self.model.user_name.ilike(search_pattern),
                    self.model.resource_id.ilike(search_pattern),
                )
            )

        where_clause = and_(*conditions) if conditions else True

        count_stmt = select(func.count(self.model.id)).where(where_clause)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        query = (
            select(self.model)
            .where(where_clause)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        items = result.scalars().all()

        return list(items), total

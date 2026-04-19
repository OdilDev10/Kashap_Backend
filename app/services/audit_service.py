"""Audit service for logging user actions."""

import json
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog, AuditAction


class AuditService:
    """Service for creating audit log entries."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        description: str | None = None,
        user_id: UUID | None = None,
        user_email: str | None = None,
        user_name: str | None = None,
        lender_id: UUID | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Create an audit log entry."""
        log_entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            lender_id=lender_id,
            extra_data=json.dumps(metadata) if metadata else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def log_create(
        self,
        resource_type: str,
        resource_id: str,
        description: str | None = None,
        user_id: UUID | None = None,
        user_email: str | None = None,
        user_name: str | None = None,
        lender_id: UUID | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a create action."""
        return await self.log(
            action=AuditAction.CREATE.value,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description or f"Created {resource_type}",
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            lender_id=lender_id,
            ip_address=ip_address,
        )

    async def log_update(
        self,
        resource_type: str,
        resource_id: str,
        description: str | None = None,
        changes: dict | None = None,
        user_id: UUID | None = None,
        user_email: str | None = None,
        user_name: str | None = None,
        lender_id: UUID | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log an update action."""
        return await self.log(
            action=AuditAction.UPDATE.value,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description or f"Updated {resource_type}",
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            lender_id=lender_id,
            metadata={"changes": changes} if changes else None,
            ip_address=ip_address,
        )

    async def log_delete(
        self,
        resource_type: str,
        resource_id: str,
        description: str | None = None,
        user_id: UUID | None = None,
        user_email: str | None = None,
        user_name: str | None = None,
        lender_id: UUID | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a delete action."""
        return await self.log(
            action=AuditAction.DELETE.value,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description or f"Deleted {resource_type}",
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            lender_id=lender_id,
            ip_address=ip_address,
        )

    async def log_payment(
        self,
        action: str,
        payment_id: str,
        amount: float,
        customer_id: UUID | None = None,
        user_id: UUID | None = None,
        user_email: str | None = None,
        user_name: str | None = None,
        lender_id: UUID | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """Log a payment-related action."""
        return await self.log(
            action=action,
            resource_type="payment",
            resource_id=payment_id,
            description=f"Payment {action}: {amount}",
            user_id=user_id,
            user_email=user_email,
            user_name=user_name,
            lender_id=lender_id,
            metadata={**(metadata or {}), "amount": amount},
            ip_address=ip_address,
        )

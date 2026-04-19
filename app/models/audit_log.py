"""Audit log model for tracking user actions across the platform."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, String, Text, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.db.base_class import Base


class AuditAction(str, Enum):
    """Audit action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "view"
    APPROVE = "approve"
    REJECT = "reject"
    SUBMIT = "submit"
    UPLOAD = "upload"
    PROCESS = "process"


class AuditLog(Base):
    """Audit log for tracking user actions.

    Records who did what, when, and on which resource.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Who performed the action
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    user_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Which tenant/lender
    lender_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # The action performed
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # What resource type (e.g., "loan", "payment", "user", "customer")
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # What specific resource (e.g., loan ID, payment ID)
    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    # Description of the change
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Extra data (JSON as string for simplicity)
    extra_data: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # IP address of the request
    ip_address: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # User agent string
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    lender = relationship("Lender", foreign_keys=[lender_id])

    # Indexes for common queries
    __table_args__ = (
        Index("ix_audit_logs_lender_created", "lender_id", "created_at"),
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.user_email} on {self.resource_type}:{self.resource_id}>"

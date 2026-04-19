"""Base model mixin with common fields."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped


class BaseModel:
    """Base mixin for all models with id, created_at, updated_at."""

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


class AuditMixin:
    """Comprehensive audit mixin for models that need full audit trail.

    Fields:
    - created_by: User who created the record
    - created_at: When the record was created (inherited from BaseModel)
    - created_from_ip: IP address where the record was created
    - updated_by: User who last updated the record
    - updated_at: When the record was last updated (inherited from BaseModel)
    - updated_from_ip: IP address where the last update occurred
    - deleted_at: Soft delete timestamp
    - deleted_by: User who soft deleted the record
    - is_deleted: Soft delete flag (alternative to deleted_at check)
    - version: Optimistic locking / revision count
    """

    # Creation audit
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    created_from_ip: Mapped[str | None] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True,
    )

    # Update audit
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    updated_from_ip: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    # Soft delete audit
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    deleted_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    # Optimistic locking
    version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    @property
    def is_deleted(self) -> bool:
        """Check if the record is soft deleted."""
        return self.deleted_at is not None


class TenantMixin:
    """Mixin for models that belong to a specific tenant/lender.

    Fields:
    - tenant_id: The lender/organization this record belongs to
    """

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
        index=True,
    )

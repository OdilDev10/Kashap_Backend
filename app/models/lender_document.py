"""Lender document model for storing legal/regulatory documents."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.db.base_class import Base
from app.core.enums import LenderDocumentType, DocumentStatus


class LenderDocument(Base):
    """Legal document uploaded by a lender for compliance/verification.

    Stores documents like RNC, operating license, trade registry, etc.
    """

    __tablename__ = "lender_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    lender_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    def __repr__(self) -> str:
        return f"<LenderDocument {self.document_type} ({self.status})>"

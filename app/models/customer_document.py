"""Customer document models - ID documents, financial statements, etc."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel
from app.core.enums import DocumentType


class CustomerDocument(Base, BaseModel):
    """Uploaded documents for customers (ID, financial statements, etc.)."""

    __tablename__ = "customer_documents"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, name="document_type_enum"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(String(50), nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, verified, rejected
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<CustomerDocument {self.document_type} - {self.file_name}>"

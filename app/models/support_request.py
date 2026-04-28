"""Support request model for public contact and report submissions."""

import uuid
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel


class SupportRequest(Base, BaseModel):
    """Support ticket/report submitted from public or authenticated flows."""

    __tablename__ = "support_requests"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    category: Mapped[Optional[str]] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(50), default="new", nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(120))
    attachments_json: Mapped[Optional[str]] = mapped_column(Text)
    context_json: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        return f"<SupportRequest {self.email}>"

"""Customer Identity Document (Cédula) OCR results."""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Enum as SQLEnum,
    Text,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel
from app.core.enums import OcrStatus


class CedulaOcrResult(Base, BaseModel):
    """OCR extraction result from Dominican ID card (Cédula)."""

    __tablename__ = "cedula_ocr_results"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_side: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "front" or "back"

    # Raw OCR data
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Extracted fields from Cédula
    detected_cedula_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    detected_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detected_birth_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detected_nationality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detected_gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    detected_expiration_date: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    detected_blood_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    detected_civil_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detected_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    detected_municipality: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # File reference
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Verification status
    matches_customer_data: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # OCR confidence
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0-1.0

    # Processing status
    status: Mapped[OcrStatus] = mapped_column(
        SQLEnum(OcrStatus),
        default=OcrStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Audit fields
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return f"<CedulaOcr {self.id} - {self.document_side}>"

    @property
    def is_valid(self) -> bool:
        """Check if OCR extraction was successful."""
        return self.status == OcrStatus.SUCCESS and self.confidence_score >= 0.7

    @property
    def extracted_cedula_raw(self) -> str | None:
        """Get the raw cedula number without formatting."""
        if self.detected_cedula_number:
            return self.detected_cedula_number.replace("-", "").replace(" ", "")
        return None

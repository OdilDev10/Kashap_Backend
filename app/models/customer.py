"""Customer model - Clientes del sistema."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Date, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel
from app.core.enums import CustomerStatus

if TYPE_CHECKING:
    from app.models.lender import Lender
    from app.models.user import User
    from app.models.customer_lender_link import CustomerLenderLink


class Customer(Base, BaseModel):
    """Cliente del sistema - solicita préstamos."""

    __tablename__ = "customers"

    lender_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(20))
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    address_line: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    province: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100), default="DO")
    status: Mapped[CustomerStatus] = mapped_column(Enum(CustomerStatus), default=CustomerStatus.ACTIVE)
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    # Relationships
    lender: Mapped["Lender"] = relationship(back_populates="customers")
    user: Mapped[Optional["User"]] = relationship(back_populates="customer_profile")
    lender_links: Mapped[list["CustomerLenderLink"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Customer {self.first_name} {self.last_name}>"

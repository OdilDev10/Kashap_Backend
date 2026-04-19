"""Client bank accounts - receive loan disbursements."""

import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.base_class import Base
from app.models.base_model import BaseModel


class ClientBankAccount(Base, BaseModel):
    """Bank account for client to receive disbursements."""

    __tablename__ = "client_bank_accounts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
    )
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # savings, checking
    account_number_masked: Mapped[str] = mapped_column(String(50), nullable=False)
    account_holder_name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="DOP")
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="active")

    def __repr__(self) -> str:
        return f"<ClientBankAccount {self.bank_name} *** {self.account_number_masked[-4:]}>"

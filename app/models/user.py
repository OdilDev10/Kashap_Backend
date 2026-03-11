from __future__ import annotations

"""User model - Usuarios internos del sistema."""

from datetime import datetime
from sqlalchemy import String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from typing import TYPE_CHECKING

from app.db.base_class import Base
from app.models.base_model import BaseModel
from app.core.enums import AccountType, UserRole, UserStatus

if TYPE_CHECKING:
    from app.models.lender import Lender
    from app.models.customer import Customer


class User(Base, BaseModel):
    """Usuario interno del sistema (pertenece a un LENDER)."""

    __tablename__ = "users"

    lender_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=True,
    )
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType),
        default=AccountType.INTERNAL,
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.AGENT)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lender: Mapped["Lender"] = relationship(back_populates="users")
    customer_profile: Mapped["Customer"] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email}>"

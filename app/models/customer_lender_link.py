"""Customer-Lender association model."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import LinkStatus
from app.db.base_class import Base
from app.models.base_model import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.lender import Lender


class CustomerLenderLink(Base, BaseModel):
    """Association row between a customer profile and a lender."""

    __tablename__ = "customer_lender_links"
    __table_args__ = (
        UniqueConstraint("customer_id", "lender_id", name="uq_customer_lender_link"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lender_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lenders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[LinkStatus] = mapped_column(
        Enum(LinkStatus),
        default=LinkStatus.LINKED,
        nullable=False,
    )

    customer: Mapped["Customer"] = relationship(back_populates="lender_links")
    lender: Mapped["Lender"] = relationship()

"""Schemas for lender CRUD operations."""

from datetime import date, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import LenderStatus, LenderType


class LenderBase(BaseModel):
    """Shared lender fields."""

    legal_name: str = Field(..., min_length=1, max_length=255)
    commercial_name: str | None = Field(default=None, max_length=255)
    lender_type: LenderType
    document_type: str = Field(..., min_length=1, max_length=50)
    document_number: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone: str = Field(..., min_length=1, max_length=20)
    address_line: str | None = Field(default=None, max_length=255)
    subscription_plan: str | None = Field(default=None, max_length=50)
    subscription_starts_at: date | None = None
    subscription_ends_at: date | None = None


class LenderCreate(LenderBase):
    """Payload for creating a lender."""

    status: LenderStatus = LenderStatus.PENDING


class LenderUpdate(BaseModel):
    """Payload for partially updating a lender."""

    legal_name: str | None = Field(default=None, min_length=1, max_length=255)
    commercial_name: str | None = Field(default=None, max_length=255)
    lender_type: LenderType | None = None
    document_type: str | None = Field(default=None, min_length=1, max_length=50)
    document_number: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=1, max_length=20)
    address_line: str | None = Field(default=None, max_length=255)
    status: LenderStatus | None = None
    subscription_plan: str | None = Field(default=None, max_length=50)
    subscription_starts_at: date | None = None
    subscription_ends_at: date | None = None


class LenderRead(LenderBase):
    """Serialized lender representation."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: LenderStatus
    created_at: datetime
    updated_at: datetime


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Simple paginated response envelope."""

    items: list[T]
    total: int
    skip: int
    limit: int

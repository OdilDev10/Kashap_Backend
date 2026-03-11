"""Customer schemas - request/response models."""

from pydantic import BaseModel, Field, EmailStr
from decimal import Decimal
from datetime import date, datetime
from typing import Optional


class CustomerCreate(BaseModel):
    """Create customer request."""
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=8, max_length=20)
    document_type: str
    document_number: str = Field(..., min_length=5, max_length=50)
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Update customer request."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None


class CustomerRead(BaseModel):
    """Customer details response."""
    customer_id: str
    lender_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    document_type: str
    document_number: str
    birth_date: Optional[date]
    gender: Optional[str]
    address_line: Optional[str]
    city: Optional[str]
    province: Optional[str]
    country: Optional[str]
    status: str
    credit_limit: Optional[Decimal]
    created_at: datetime


class CustomerListItem(BaseModel):
    """Customer list item."""
    customer_id: str
    first_name: str
    last_name: str
    email: str
    status: str
    created_at: datetime


class CustomerSummary(BaseModel):
    """Customer summary with loan statistics."""
    customer_id: str
    first_name: str
    last_name: str
    email: str
    status: str
    credit_limit: Optional[Decimal]
    active_loans_count: int
    total_debt: Decimal
    overdue_installments_count: int

"""User schemas - request/response models."""

from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    """Create user request."""
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(..., min_length=8)
    role: str = Field(..., regex="^(owner|manager|agent|reviewer)$")


class UserUpdate(BaseModel):
    """Update user request."""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None


class UserRead(BaseModel):
    """User details response."""
    user_id: str
    lender_id: Optional[str]
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    role: str
    status: str
    last_login_at: Optional[datetime]
    created_at: datetime


class UserListItem(BaseModel):
    """User list item."""
    user_id: str
    first_name: str
    last_name: str
    email: str
    role: str
    status: str
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str = Field(..., min_length=8)


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    new_password: str = Field(..., min_length=8)

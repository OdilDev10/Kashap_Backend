"""Authentication request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Login request."""

    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response with access and refresh tokens."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)


class RegisterResponse(BaseModel):
    """Registration response."""

    user_id: str
    email: str
    status: str
    message: str


class RegisterCustomerRequest(BaseModel):
    """Customer self-registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., min_length=3, max_length=20)
    document_type: str = Field(..., min_length=2, max_length=50)
    document_number: str = Field(..., min_length=3, max_length=50)
    lender_id: str


class RegisterLenderRequest(BaseModel):
    """Lender self-registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    legal_name: str = Field(..., min_length=3, max_length=255)
    lender_type: str = Field(..., min_length=2, max_length=50)
    document_type: str = Field(..., min_length=2, max_length=50)
    document_number: str = Field(..., min_length=3, max_length=50)
    phone: str = Field(..., min_length=3, max_length=20)


class RegistrationEntityResponse(BaseModel):
    """Registration response for customer or lender onboarding."""

    email: str
    status: str
    message: str
    user_id: str | None = None
    lender_id: str | None = None
    customer_id: str | None = None


class VerifyEmailRequest(BaseModel):
    """Email verification request."""

    token: str


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Password reset request."""

    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    """Change password request for authenticated user."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class SendOTPRequest(BaseModel):
    """Send OTP request."""

    pass  # OTP is sent based on authenticated user


class VerifyOTPRequest(BaseModel):
    """Verify OTP request."""

    otp_code: str = Field(..., min_length=6, max_length=6)


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    first_name: str
    last_name: str
    role: str
    account_type: str | None = None
    status: Optional[str] = None
    lender_id: str | None = None
    phone: str | None = None
    last_login_at: datetime | None = None
    roles: list[str] = []
    permissions: list[str] = []


class AppConfigResponse(BaseModel):
    """Bootstrap configuration for the client application."""

    app_name: str
    version: str
    environment: str
    features: dict[str, bool]


class AuthResponse(BaseModel):
    """Complete auth response with user info."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

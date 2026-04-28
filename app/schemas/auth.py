"""Authentication request/response schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


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
    phone: str = Field(..., min_length=3, max_length=20)
    cedula: str = Field(..., min_length=11, max_length=20)


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
    cedula: str | None = Field(default=None, min_length=11, max_length=20)
    # Legacy fields (backward compatibility)
    document_type: str | None = Field(default=None, min_length=2, max_length=50)
    document_number: str | None = Field(default=None, min_length=3, max_length=50)
    lender_id: str

    @model_validator(mode="after")
    def ensure_cedula(self):
        if self.cedula:
            return self
        if self.document_number and (self.document_type or "").strip().lower() in {
            "cedula",
            "cédula",
        }:
            self.cedula = self.document_number
            return self
        raise ValueError("La cédula es obligatoria para registrar clientes")


class RegisterLenderRequest(BaseModel):
    """Lender self-registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    legal_name: str = Field(..., min_length=3, max_length=255)
    commercial_name: str = Field(..., min_length=2, max_length=255)
    lender_type: str = Field(..., min_length=2, max_length=50)
    rnc_number: str | None = Field(default=None, min_length=9, max_length=20)
    owner_cedula: str | None = Field(default=None, min_length=11, max_length=20)
    phone: str = Field(..., min_length=3, max_length=20)
    # Legacy fields (backward compatibility)
    document_type: str | None = Field(default=None, min_length=2, max_length=50)
    document_number: str | None = Field(default=None, min_length=3, max_length=50)

    @model_validator(mode="after")
    def ensure_required_docs(self):
        if not self.rnc_number:
            if (self.document_type or "").strip().lower() == "rnc" and self.document_number:
                self.rnc_number = self.document_number
        if not self.rnc_number:
            raise ValueError("El RNC es obligatorio para registrar prestamistas")
        if not self.owner_cedula:
            raise ValueError("La cédula del titular es obligatoria")
        return self


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

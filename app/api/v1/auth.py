"""Authentication endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshTokenRequest, RegisterRequest,
    RegisterResponse, VerifyEmailRequest, ForgotPasswordRequest,
    ResetPasswordRequest, ChangePasswordRequest, SendOTPRequest,
    VerifyOTPRequest, AuthResponse, UserResponse,
    RegisterCustomerRequest, RegisterLenderRequest, RegistrationEntityResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
from app.models.user import User


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register new user with email verification."""
    service = AuthService(session)
    result = await service.register(
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
    )
    return RegisterResponse(**result)


@router.post("/register/customer", response_model=RegistrationEntityResponse, status_code=status.HTTP_201_CREATED)
async def register_customer(
    request: RegisterCustomerRequest,
    session: AsyncSession = Depends(get_db),
) -> RegistrationEntityResponse:
    """Register a customer account."""
    service = AuthService(session)
    names = request.full_name.strip().split()
    first_name = names[0]
    last_name = " ".join(names[1:]) if len(names) > 1 else "Cliente"
    result = await service.register_customer(
        email=request.email,
        password=request.password,
        first_name=first_name,
        last_name=last_name,
        lender_id=request.lender_id,
        document_type=request.document_type,
        document_number=request.document_number,
        phone=request.phone,
    )
    return RegistrationEntityResponse(**result)


@router.post("/register/lender", response_model=RegistrationEntityResponse, status_code=status.HTTP_201_CREATED)
async def register_lender(
    request: RegisterLenderRequest,
    session: AsyncSession = Depends(get_db),
) -> RegistrationEntityResponse:
    """Register a lender account."""
    service = AuthService(session)
    result = await service.register_lender(
        email=request.email,
        password=request.password,
        legal_name=request.legal_name,
        lender_type=request.lender_type,
        document_type=request.document_type,
        document_number=request.document_number,
        phone=request.phone,
    )
    return RegistrationEntityResponse(**result)


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: VerifyEmailRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Verify user email with token."""
    service = AuthService(session)
    result = await service.verify_email(request.token)
    return MessageResponse(message=result.get("message", "Email verified"))


@router.post("/login", response_model=AuthResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """Login user and return access/refresh tokens."""
    service = AuthService(session)
    result = await service.login(request.email, request.password)
    return AuthResponse(**result)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    service = AuthService(session)
    result = await service.refresh_token_service(request.refresh_token)
    return TokenResponse(**result)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_user),
) -> MessageResponse:
    """Logout user (client should discard tokens)."""
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user profile."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        role=getattr(current_user.role, "value", current_user.role),
        account_type=getattr(current_user.account_type, "value", current_user.account_type),
        status=getattr(current_user.status, "value", current_user.status),
        lender_id=str(current_user.lender_id) if current_user.lender_id else None,
        phone=current_user.phone,
        last_login_at=current_user.last_login_at,
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Request password reset via email."""
    service = AuthService(session)
    result = await service.forgot_password(request.email)
    return MessageResponse(message=result.get("message", "Email sent if exists"))


@router.post("/verify-reset-token", response_model=MessageResponse)
async def verify_reset_token(
    request: VerifyEmailRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Verify that reset token is valid."""
    service = AuthService(session)
    result = await service.verify_reset_token(request.token)
    return MessageResponse(message=result.get("message", "Token is valid"))


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reset password with token."""
    service = AuthService(session)
    result = await service.reset_password(request.token, request.new_password)
    return MessageResponse(message=result.get("message", "Password reset successfully"))


@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(
    request: SendOTPRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Send OTP to authenticated user."""
    service = AuthService(session)
    result = await service.send_otp(str(current_user.id))
    return MessageResponse(message=result.get("message", "OTP sent"))


@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp(
    request: VerifyOTPRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Verify OTP code."""
    service = AuthService(session)
    result = await service.verify_otp(str(current_user.id), request.otp_code)
    return MessageResponse(message=result.get("message", "OTP verified"))


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Change password for authenticated user."""
    service = AuthService(session)
    result = await service.change_password(
        str(current_user.id),
        request.current_password,
        request.new_password,
    )
    return MessageResponse(message=result.get("message", "Password changed"))

"""User management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.core.exceptions import AppException

router = APIRouter(prefix="/users", tags=["users"])


class UserCreateRequest(BaseModel):
    """Create user request."""
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    role: str
    password: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str
    new_password: str


@router.get("/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get current user profile."""
    return {
        "user_id": str(current_user.id),
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone": current_user.phone,
        "role": current_user.role,
        "status": current_user.status,
        "account_type": current_user.account_type,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Change user password."""
    try:
        from app.services.auth_service import AuthService
        service = AuthService(session)
        result = await service.change_password(
            current_user.id,
            request.current_password,
            request.new_password,
        )
        return result
    except AppException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

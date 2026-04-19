"""Reusable FastAPI dependencies for auth and authorization."""

from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repo import UserRepository


security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Authentication credentials were not provided")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid access token")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Token subject is missing")

    user = await UserRepository(session).get_or_404(user_id, error_code="USER_NOT_FOUND")
    return user


async def get_current_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Return validated access-token claims without DB lookup."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedException("Authentication credentials were not provided")

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise UnauthorizedException("Invalid access token")

    if not payload.get("sub"):
        raise UnauthorizedException("Token subject is missing")

    return payload


async def get_lender_context(current_user: User = Depends(get_current_user)) -> str:
    """Return the authenticated lender context when available."""
    if current_user.lender_id is None:
        raise ForbiddenException("Authenticated user is not scoped to a lender")

    return str(current_user.lender_id)


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Build a dependency that restricts access to the provided roles."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        user_role = getattr(current_user.role, "value", current_user.role)
        if user_role not in allowed_roles:
            raise ForbiddenException("You do not have permission to access this resource")
        return current_user

    return dependency

"""Password reset repository."""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.auth import PasswordReset


class PasswordResetRepository(BaseRepository[PasswordReset]):
    """Repository for PasswordReset operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, PasswordReset)

    async def get_by_token(self, token: str) -> PasswordReset | None:
        """Get reset record by token."""
        stmt = select(PasswordReset).where(PasswordReset.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID) -> PasswordReset | None:
        """Get latest reset for user."""
        stmt = (
            select(PasswordReset)
            .where(PasswordReset.user_id == user_id)
            .order_by(PasswordReset.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_expired(self) -> int:
        """Delete expired reset tokens."""
        from sqlalchemy import delete
        stmt = delete(PasswordReset).where(
            PasswordReset.expires_at < datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

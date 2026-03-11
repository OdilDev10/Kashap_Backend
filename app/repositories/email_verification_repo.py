"""Email verification repository."""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.auth import EmailVerification


class EmailVerificationRepository(BaseRepository[EmailVerification]):
    """Repository for EmailVerification operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, EmailVerification)

    async def get_by_token(self, token: str) -> EmailVerification | None:
        """Get verification record by token."""
        stmt = select(EmailVerification).where(EmailVerification.token == token)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID) -> EmailVerification | None:
        """Get latest verification for user."""
        stmt = (
            select(EmailVerification)
            .where(EmailVerification.user_id == user_id)
            .order_by(EmailVerification.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def cleanup_expired(self) -> int:
        """Delete expired verification tokens."""
        from sqlalchemy import delete
        stmt = delete(EmailVerification).where(
            EmailVerification.expires_at < datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

"""OTP repository."""

from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.auth import OTP


class OTPRepository(BaseRepository[OTP]):
    """Repository for OTP operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, OTP)

    async def get_by_code(self, code: str, user_id: UUID) -> OTP | None:
        """Get OTP by code for specific user."""
        stmt = select(OTP).where(
            (OTP.code == code) & (OTP.user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_user(self, user_id: UUID) -> OTP | None:
        """Get latest OTP for user."""
        stmt = (
            select(OTP)
            .where(OTP.user_id == user_id)
            .order_by(OTP.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user(self, user_id: UUID) -> list[OTP]:
        """Get all OTPs for user."""
        stmt = select(OTP).where(OTP.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def cleanup_expired(self) -> int:
        """Delete expired OTP codes."""
        from sqlalchemy import delete
        stmt = delete(OTP).where(
            OTP.expires_at < datetime.utcnow()
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

    async def cleanup_verified(self, days: int = 7) -> int:
        """Delete old verified OTPs."""
        from sqlalchemy import delete
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = delete(OTP).where(
            (OTP.verified_at.isnot(None)) & (OTP.verified_at < cutoff)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount

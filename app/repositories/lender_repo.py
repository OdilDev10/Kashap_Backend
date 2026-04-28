"""Repository for lender persistence operations."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LenderStatus
from app.models.lender import Lender, LenderBankAccount, LenderInvitation
from app.repositories.base import BaseRepository


class LenderRepository(BaseRepository[Lender]):
    """Repository with lender-specific lookup helpers."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Lender)

    async def get_by_email(self, email: str) -> Lender | None:
        """Return a lender by normalized email."""
        stmt = select(Lender).where(Lender.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_document_number(self, document_number: str) -> Lender | None:
        """Return a lender by legal document number."""
        stmt = select(Lender).where(Lender.document_number == document_number.strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def owner_cedula_exists(self, owner_cedula: str) -> bool:
        """Check if owner cedula is already registered in another lender."""
        stmt = select(Lender.id).where(Lender.owner_cedula == owner_cedula.strip())
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def phone_exists(self, phone: str) -> bool:
        """Check if lender phone already exists."""
        stmt = select(Lender.id).where(Lender.phone == phone.strip())
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def get_by_status(self, status: LenderStatus) -> list[Lender]:
        """Get all lenders with specific status."""
        stmt = select(Lender).where(Lender.status == status)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists_with_identity(
        self,
        *,
        email: str,
        document_number: str,
        exclude_id: UUID | None = None,
    ) -> bool:
        """Check whether another lender already uses the provided identity fields."""
        stmt = select(Lender.id).where(
            or_(
                Lender.email == email.lower().strip(),
                Lender.document_number == document_number.strip(),
            ),
        )

        if exclude_id is not None:
            stmt = stmt.where(Lender.id != exclude_id)

        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None


class LenderInvitationRepository(BaseRepository[LenderInvitation]):
    """Repository for LenderInvitation operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, LenderInvitation)

    async def get_by_code(self, code: str) -> LenderInvitation | None:
        """Get invitation by code."""
        stmt = select(LenderInvitation).where(LenderInvitation.code == code)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_lender(self, lender_id: UUID) -> list[LenderInvitation]:
        """Get all active invitations for a lender."""
        stmt = select(LenderInvitation).where(
            LenderInvitation.lender_id == lender_id,
            LenderInvitation.status == "active",
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class LenderBankAccountRepository(BaseRepository[LenderBankAccount]):
    """Repository for LenderBankAccount operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, LenderBankAccount)

    async def get_by_lender(self, lender_id: UUID) -> list[LenderBankAccount]:
        """Get all bank accounts for a lender."""
        stmt = select(LenderBankAccount).where(LenderBankAccount.lender_id == lender_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_primary_by_lender(self, lender_id: UUID) -> LenderBankAccount | None:
        """Get primary bank account for a lender."""
        stmt = select(LenderBankAccount).where(
            LenderBankAccount.lender_id == lender_id,
            LenderBankAccount.is_primary == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

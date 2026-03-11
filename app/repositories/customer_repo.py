"""Repository for Customer model - database operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository for Customer CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Customer)

    async def get_by_email(self, email: str) -> Customer | None:
        """Get customer by email."""
        stmt = select(Customer).where(Customer.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_document_number(self, document_number: str) -> Customer | None:
        """Get customer by document number."""
        stmt = select(Customer).where(Customer.document_number == document_number.strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_lender(self, lender_id: UUID) -> list[Customer]:
        """Get all customers for a lender."""
        stmt = select(Customer).where(Customer.lender_id == lender_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        customer = await self.get_by_email(email)
        return customer is not None

    async def document_exists(self, document_number: str, exclude_id: UUID | None = None) -> bool:
        """Check if document number exists (optionally excluding a specific customer)."""
        stmt = select(Customer).where(Customer.document_number == document_number.strip())
        if exclude_id:
            stmt = stmt.where(Customer.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

"""User repository for database operations."""

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.enums import UserRole
from app.repositories.base import BaseRepository
from app.models.user import User


class UserRepository(BaseRepository[User]):
    """Repository for User entity operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_or_404(self, email: str) -> User:
        """Get user by email, raise 404 if not found."""
        user = await self.get_by_email(email)
        if not user:
            raise Exception(f"User with email {email} not found")
        return user

    async def get_by_lender(self, lender_id: UUID) -> list[User]:
        """Get all users for a specific lender."""
        stmt = select(User).where(User.lender_id == lender_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def email_exists(self, email: str) -> bool:
        """Check if email already exists."""
        return await self.exists(email=email.lower())

    async def create_user(self, **kwargs) -> User:
        """Create new user."""
        # Normalize email to lowercase
        if "email" in kwargs:
            kwargs["email"] = kwargs["email"].lower()
        return await self.create(kwargs)

    async def phone_exists(self, phone: str) -> bool:
        """Check if phone already exists."""
        stmt = select(User.id).where(User.phone == phone.strip())
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def document_exists(self, document_number: str) -> bool:
        """Check if document number already exists."""
        stmt = select(User.id).where(User.document_number == document_number.strip())
        result = await self.session.execute(stmt.limit(1))
        return result.scalar_one_or_none() is not None

    async def get_by_lender_and_role(self, lender_id: UUID, role: UserRole) -> list[User]:
        """Get all users with a specific role in a lender."""
        stmt = select(User).where(User.lender_id == lender_id, User.role == role)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_platform_admins(self) -> list[User]:
        """Get all platform admins (users without a lender_id)."""
        stmt = select(User).where(User.lender_id == None, User.role == UserRole.PLATFORM_ADMIN)
        result = await self.session.execute(stmt)
        return result.scalars().all()

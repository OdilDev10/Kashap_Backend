"""Base repository with generic CRUD operations for all entities."""

from typing import Generic, TypeVar, List, Optional, Tuple, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from app.core.exceptions import NotFoundException

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Generic async repository with CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get(self, id: UUID) -> Optional[T]:
        """Get entity by id, returns None if not found."""
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_404(self, id: UUID, error_code: str = "NOT_FOUND") -> T:
        """Get entity by id, raises NotFoundException if not found."""
        entity = await self.get(id)
        if not entity:
            raise NotFoundException(
                message=f"{self.model.__name__} not found",
                code=error_code
            )
        return entity

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[T], int]:
        """List entities with optional filters, returns (items, total_count)."""
        query = select(self.model)

        # Apply filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)

        # Get total count
        count_stmt = select(func.count(self.model.id))
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    count_stmt = count_stmt.where(getattr(self.model, key) == value)
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def create(self, data: Dict[str, Any]) -> T:
        """Create new entity."""
        entity = self.model(**data)
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def update(self, entity: T, data: Dict[str, Any]) -> T:
        """Update entity with new data."""
        for key, value in data.items():
            if hasattr(entity, key) and value is not None:
                setattr(entity, key, value)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        """Delete entity."""
        await self.session.delete(entity)
        await self.session.flush()

    async def save(self) -> None:
        """Commit changes to database."""
        await self.session.commit()

    async def exists(self, **filters) -> bool:
        """Check if entity exists with given filters."""
        stmt = select(func.count(self.model.id))
        for key, value in filters.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        result = await self.session.execute(stmt)
        return (result.scalar() or 0) > 0

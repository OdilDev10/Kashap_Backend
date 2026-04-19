"""Notification repository."""

from uuid import UUID
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select, func, desc, and_

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository for Notification model."""

    def __init__(self, session):
        super().__init__(session, Notification)

    async def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Notification], int]:
        """Get notifications for a user."""
        conditions = [Notification.user_id == user_id]

        if unread_only:
            conditions.append(Notification.is_read == False)

        query = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(desc(Notification.created_at))
            .offset(skip)
            .limit(limit)
        )

        count_query = select(func.count(Notification.id)).where(and_(*conditions))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        result = await self.session.execute(query)
        return result.scalars().all(), total

    async def mark_as_read(
        self, notification_id: UUID, user_id: UUID
    ) -> Optional[Notification]:
        """Mark notification as read if it belongs to user."""
        notification = await self.get(notification_id)
        if notification and str(notification.user_id) == str(user_id):
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.session.flush()
            return notification
        return None

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Mark all notifications as read for user. Returns count of updated."""
        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
        )
        count = result.scalar() or 0

        await self.session.execute(
            Notification.__table__.update()
            .where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
            .values(is_read=True, read_at=datetime.now(timezone.utc))
        )
        await self.session.flush()
        return count

    async def get_unread_count(self, user_id: UUID) -> int:
        """Get count of unread notifications."""
        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read == False,
                )
            )
        )
        return result.scalar() or 0

    async def delete_old_notifications(self, days: int = 30) -> int:
        """Delete notifications older than days. Returns count deleted."""
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.session.execute(
            select(func.count(Notification.id)).where(Notification.created_at < cutoff)
        )
        count = result.scalar() or 0

        await self.session.execute(
            Notification.__table__.delete().where(Notification.created_at < cutoff)
        )
        await self.session.flush()
        return count

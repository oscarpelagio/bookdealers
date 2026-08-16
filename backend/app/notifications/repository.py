"""Repositorio de persistencia del módulo notifications.

Solo operaciones de base de datos; sin lógica de negocio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.notifications.models import Notification, NotificationSetting

if TYPE_CHECKING:
    CursorAfter = tuple[datetime, uuid.UUID] | None
else:
    CursorAfter = object


class NotificationsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Notification ----------

    async def list_notifications(
        self, recipient_id: uuid.UUID, *, limit: int, after: CursorAfter
    ) -> list[Notification]:
        stmt = select(Notification).where(Notification.recipient_id == recipient_id)
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where(
                (Notification.created_at, Notification.id) < (created_at, row_id)
            )
        stmt = stmt.order_by(
            Notification.created_at.desc(), Notification.id.desc()
        ).limit(limit)
        return (await self.db.exec(stmt)).all()

    async def count_unread(self, recipient_id: uuid.UUID) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.recipient_id == recipient_id,
            Notification.read_at.is_(None),
        )
        return (await self.db.exec(stmt)).one()

    async def get_notification(self, notification_id: uuid.UUID) -> Notification | None:
        return await self.db.get(Notification, notification_id)

    async def mark_read(self, notification: Notification, read_at: datetime) -> None:
        notification.read_at = read_at

    async def mark_all_read(self, recipient_id: uuid.UUID, read_at: datetime) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.recipient_id == recipient_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        result = await self.db.exec(stmt)
        return result.rowcount or 0

    # ---------- Settings ----------

    async def get_setting(self, user_id: uuid.UUID) -> NotificationSetting | None:
        stmt = select(NotificationSetting).where(
            NotificationSetting.user_id == user_id
        )
        return (await self.db.exec(stmt)).first()

    async def create_setting(self, user_id: uuid.UUID) -> NotificationSetting:
        setting = NotificationSetting(user_id=user_id)
        self.db.add(setting)
        await self.db.flush()
        return setting

    # ---------- Usuarios para respuestas ----------

    async def get_users_by_ids(self, ids: list[uuid.UUID]) -> list[User]:
        if not ids:
            return []
        stmt = select(User).where(User.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_profiles_by_user_ids(self, ids: list[uuid.UUID]) -> list:
        from app.profiles.models import Profile

        if not ids:
            return []
        stmt = select(Profile).where(Profile.user_id.in_(ids))
        return (await self.db.exec(stmt)).all()

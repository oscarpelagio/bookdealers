"""Dependencias de DI del módulo notifications.

Al importarse este módulo (vía el router) se registran los handlers de
eventos que crean notificaciones a partir de los eventos de F4/F6.
"""

from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_db
from app.notifications.handlers import register
from app.notifications.repository import NotificationsRepository
from app.notifications.service import NotificationsService

register()


def get_notifications_repository(
    db: AsyncSession = Depends(get_db),
) -> NotificationsRepository:
    return NotificationsRepository(db)


def get_notifications_service(
    repo: NotificationsRepository = Depends(get_notifications_repository),
    db: AsyncSession = Depends(get_db),
) -> NotificationsService:
    return NotificationsService(repo, db)

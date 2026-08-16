"""Endpoints del módulo notifications (routers finos, sin lógica).

Rutas:
- `GET /notifications` (cursor + unread_count) · `POST /notifications/read`
- `PATCH /notifications/{id}/read` · `GET|PATCH /notifications/settings`
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.notifications.dependencies import get_notifications_service
from app.notifications.schemas import (
    MarkAllReadResponse,
    NotificationPage,
    NotificationReadResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from app.notifications.service import NotificationsService

router = APIRouter()


@router.get(
    "/notifications",
    response_model=NotificationPage,
    summary="Mi bandeja de notificaciones (paginado por cursor + unread_count)",
)
async def list_notifications(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: NotificationsService = Depends(get_notifications_service),
) -> NotificationPage:
    return await service.list_notifications(user, cursor=cursor, limit=limit)


@router.post(
    "/notifications/read",
    response_model=MarkAllReadResponse,
    summary="Marcar todas las notificaciones como leídas",
)
async def mark_all_read(
    user: User = Depends(get_current_user),
    service: NotificationsService = Depends(get_notifications_service),
) -> MarkAllReadResponse:
    return await service.mark_all_read(user)


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationReadResponse,
    summary="Marcar una notificación como leída",
)
async def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: NotificationsService = Depends(get_notifications_service),
) -> NotificationReadResponse:
    return await service.mark_read(user, notification_id)


@router.get(
    "/notifications/settings",
    response_model=NotificationSettingsResponse,
    summary="Mis preferencias de notificaciones",
)
async def get_settings(
    user: User = Depends(get_current_user),
    service: NotificationsService = Depends(get_notifications_service),
) -> NotificationSettingsResponse:
    return await service.get_settings(user)


@router.patch(
    "/notifications/settings",
    response_model=NotificationSettingsResponse,
    summary="Actualizar preferencias de notificaciones",
)
async def update_settings(
    payload: NotificationSettingsUpdate,
    user: User = Depends(get_current_user),
    service: NotificationsService = Depends(get_notifications_service),
) -> NotificationSettingsResponse:
    return await service.update_settings(
        user, fields=payload.model_dump(exclude_unset=True)
    )

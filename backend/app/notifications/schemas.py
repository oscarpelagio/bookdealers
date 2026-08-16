"""Esquemas de validación del módulo notifications."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field
from sqlmodel import SQLModel

from app.enums import NotificationType, ObjectType
from app.social.schemas import UserBrief


class NotificationResponse(SQLModel):
    """Notificación de la bandeja de entrada."""

    id: str
    type: NotificationType
    actor: UserBrief | None = None
    object_type: ObjectType | None = None
    object_id: str | None = None
    message: str | None = None
    read: bool = False
    created_at: datetime


class NotificationPage(SQLModel):
    """Página de notificaciones (cursor pagination) + contador unread."""

    items: list[NotificationResponse]
    next: str | None = None
    unread_count: int = 0


class MarkAllReadResponse(SQLModel):
    """Número de notificaciones marcadas como leídas."""

    read: int


class NotificationReadResponse(SQLModel):
    """Resultado de marcar una notificación como leída."""

    id: str
    read: bool


class NotificationSettingsResponse(SQLModel):
    """Preferencias de notificaciones del usuario."""

    user_id: str
    email_digest_enabled: bool
    in_app_master: bool
    exceptions: dict[str, dict[str, bool]] = {}


class NotificationSettingsUpdate(SQLModel):
    """Cuerpo para actualizar preferencias."""

    email_digest_enabled: bool | None = None
    in_app_master: bool | None = None
    exceptions: dict[str, dict[str, bool]] | None = None


class NotificationCreate(SQLModel):
    """(uso interno/tests) Notificación manual."""

    recipient_id: uuid.UUID
    type: NotificationType
    actor_id: uuid.UUID | None = None
    object_type: ObjectType | None = None
    object_id: uuid.UUID | None = None
    message: str | None = None

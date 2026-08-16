"""Lógica de dominio del módulo notifications (FASE 8).

La creación de notificaciones la hacen los handlers de eventos
(`handlers.py`). Este servicio gestiona la bandeja (lectura/mark read) y
las preferencias por usuario.
"""

from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.pagination import decode_cursor, encode_cursor
from app.core.time import utcnow
from app.enums import NotificationType
from app.notifications.exceptions import (
    InvalidNotificationSettingsError,
    NotificationNotFoundError,
)
from app.notifications.models import Notification, NotificationSetting
from app.notifications.repository import NotificationsRepository
from app.notifications.schemas import (
    MarkAllReadResponse,
    NotificationPage,
    NotificationReadResponse,
    NotificationResponse,
    NotificationSettingsResponse,
)
from app.social.schemas import UserBrief

_VALID_CHANNELS = ("in_app", "email")


class NotificationsService:
    def __init__(self, repo: NotificationsRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    # ---------- Bandeja ----------

    async def list_notifications(
        self, user: User, *, cursor: str | None, limit: int
    ) -> NotificationPage:
        after = decode_cursor(cursor)
        notifications = await self.repo.list_notifications(
            user.id, limit=limit + 1, after=after
        )
        has_more = len(notifications) > limit
        page = notifications[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        unread_count = await self.repo.count_unread(user.id)
        items = await self._responses(page)
        return NotificationPage(
            items=items, next=next_cursor, unread_count=unread_count
        )

    async def mark_all_read(self, user: User) -> MarkAllReadResponse:
        count = await self.repo.mark_all_read(user.id, utcnow())
        await self.db.commit()
        return MarkAllReadResponse(read=count)

    async def mark_read(
        self, user: User, notification_id: uuid.UUID
    ) -> NotificationReadResponse:
        notification = await self.repo.get_notification(notification_id)
        if (
            notification is None
            or notification.recipient_id != user.id
            or notification.read_at is not None
        ):
            raise NotificationNotFoundError()
        await self.repo.mark_read(notification, utcnow())
        await self.db.commit()
        return NotificationReadResponse(id=str(notification_id), read=True)

    # ---------- Settings ----------

    async def get_settings(self, user: User) -> NotificationSettingsResponse:
        setting = await self.repo.get_setting(user.id)
        if setting is None:
            setting = await self.repo.create_setting(user.id)
            await self.db.commit()
            await self.db.refresh(setting)
        return self._settings_response(setting)

    async def update_settings(
        self, user: User, *, fields: dict
    ) -> NotificationSettingsResponse:
        setting = await self.repo.get_setting(user.id)
        if setting is None:
            setting = await self.repo.create_setting(user.id)

        if "email_digest_enabled" in fields:
            setting.email_digest_enabled = fields["email_digest_enabled"]
        if "in_app_master" in fields:
            setting.in_app_master = fields["in_app_master"]
        if "exceptions" in fields:
            setting.exceptions = self._validate_exceptions(fields["exceptions"])
        setting.updated_at = utcnow()

        await self.db.commit()
        await self.db.refresh(setting)
        return self._settings_response(setting)

    # ---------- Helpers ----------

    @staticmethod
    def _validate_exceptions(exceptions: dict) -> dict:
        """Valida y normaliza el JSONB de excepciones por tipo."""
        valid_types = {t.value for t in NotificationType}
        result: dict[str, dict[str, bool]] = {}
        for key, value in exceptions.items():
            if key not in valid_types or not isinstance(value, dict):
                raise InvalidNotificationSettingsError()
            normalized = {}
            for channel in _VALID_CHANNELS:
                val = value.get(channel, channel == "in_app")
                if not isinstance(val, bool):
                    raise InvalidNotificationSettingsError()
                normalized[channel] = val
            result[key] = normalized
        return result

    @staticmethod
    def _settings_response(setting: NotificationSetting) -> NotificationSettingsResponse:
        return NotificationSettingsResponse(
            user_id=str(setting.user_id),
            email_digest_enabled=setting.email_digest_enabled,
            in_app_master=setting.in_app_master,
            exceptions=setting.exceptions or {},
        )

    async def _responses(
        self, notifications: list[Notification]
    ) -> list[NotificationResponse]:
        if not notifications:
            return []

        actor_ids = [n.actor_id for n in notifications if n.actor_id]
        users = {u.id: u for u in await self.repo.get_users_by_ids(actor_ids)}
        profiles = {
            p.user_id: p for p in await self.repo.get_profiles_by_user_ids(actor_ids)
        }

        briefs: dict[uuid.UUID, UserBrief] = {}
        for actor_id in set(actor_ids):
            user = users.get(actor_id)
            if user is None:
                continue
            profile = profiles.get(actor_id)
            briefs[actor_id] = UserBrief(
                id=str(actor_id),
                username=user.username,
                display_name=profile.display_name if profile else None,
                avatar_url=profile.avatar_url if profile else None,
            )

        result: list[NotificationResponse] = []
        for notification in notifications:
            actor = briefs.get(notification.actor_id) if notification.actor_id else None
            result.append(
                NotificationResponse(
                    id=str(notification.id),
                    type=notification.type,
                    actor=actor,
                    object_type=notification.object_type,
                    object_id=str(notification.object_id) if notification.object_id else None,
                    message=notification.message,
                    read=notification.read_at is not None,
                    created_at=notification.created_at,
                )
            )
        return result

"""Models del context NOTIFICATIONS (FASE 8).

Diseño (documento de arquitectura §2.25–2.27):
- `Notification`: bandeja de entrada del usuario. `actor_id` ON DELETE
  SET NULL (si el actor se borra, la notificación queda anónima);
  `object_type`/`object_id` sin FK (referencias a contenido).
- `NotificationSetting`: preferencias por usuario (1:1). `exceptions`
  es un JSONB `{tipo: {"in_app": bool, "email": bool}}` para no añadir
  decenas de columnas booleanas (validado en el schema/service).
- `PushQueue`: cola técnica de entregas (EMAIL/PUSH) para un worker
  posterior; en esta fase solo se encola cuando el setting lo permite.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.enums import Channel, NotificationType, ObjectType, PushStatus


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


def _uuid_pk():
    return Column(PgUUID(as_uuid=True), primary_key=True)


class Notification(SQLModel, table=True):
    """Notificación de la bandeja de entrada del usuario."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_read", "recipient_id", "read_at"),
        Index(
            "ix_notifications_recipient_unread",
            "recipient_id",
            text("created_at DESC"),
            postgresql_where=text("read_at IS NULL"),
        ),
        Index("ix_notifications_created", text("created_at DESC")),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    recipient_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    actor_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    type: NotificationType = Field(
        sa_column=Column(
            SAEnum(NotificationType, name="notification_type"), nullable=False
        )
    )
    object_type: ObjectType | None = Field(
        default=None,
        sa_column=Column(SAEnum(ObjectType, name="object_type"), nullable=True),
    )
    object_id: uuid.UUID | None = Field(
        default=None, sa_column=Column(PgUUID(as_uuid=True), nullable=True)
    )
    message: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    read_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))


class NotificationSetting(SQLModel, table=True):
    """Preferencias de notificaciones de un usuario (1:1)."""

    __tablename__ = "notification_settings"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_notification_settings_user"),
        Index("ix_notification_settings_user", "user_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    email_digest_enabled: bool = Field(
        sa_column=Column(Boolean, nullable=False, default=False)
    )
    in_app_master: bool = Field(
        sa_column=Column(Boolean, nullable=False, default=True)
    )
    exceptions: dict = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False, default=dict)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    updated_at: datetime = Field(sa_column=_datetime(required=True))


class PushQueue(SQLModel, table=True):
    """Cola técnica de entregas (EMAIL/PUSH) para un worker posterior."""

    __tablename__ = "push_queue"
    __table_args__ = (
        Index("ix_push_queue_status_next", "status", "next_attempt_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    channel: Channel = Field(
        sa_column=Column(SAEnum(Channel, name="channel"), nullable=False)
    )
    payload: dict = Field(sa_column=Column(JSONB, nullable=False))
    status: PushStatus = Field(
        default=PushStatus.PENDING,
        sa_column=Column(SAEnum(PushStatus, name="push_status"), nullable=False),
    )
    attempts: int = Field(sa_column=Column(Integer, nullable=False, default=0))
    next_attempt_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    sent_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )

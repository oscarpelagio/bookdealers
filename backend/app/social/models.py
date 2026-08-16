"""Models del context SOCIAL GRAPH (FASE 4).

Diseño (documento de arquitectura §1.7 y §2.12–2.16):
- `Follow`: relación unidireccional follower → followee. UNIQUE (follower,
  followee), CHECK no auto-follow. El service borra la fila (y la reversa)
  cuando se crea un Block.
- `Block`: UNIQUE (blocker, blocked). Borra Follows a dos sentidos y activa
  visibilidad de ocultado (ADR-4).
- `Mute`: como Block pero solo silencia el feed (no oculta mecánicamente).
- `Report`: polimórfico (target_type/target_id sin FK), status OPEN por
  defecto.
- `Activity`: log append-only de eventos de UX (no el bus de eventos).
  `visibility` se copia de la privacidad del actor al crearse. actor
  ON DELETE SET NULL (si el usuario se borra, la actividad queda anónima).

`object_type`/`object_id` son opcionales: verbos como FOLLOWED solo usan
`target_type`/`target_id` (el usuario seguido). Timestamps UTC.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlmodel import Field, SQLModel

from app.core.time import utcnow
from app.enums import ActivityVerb, ObjectType, ReportStatus, ReportTarget, Visibility


def _datetime(required: bool = True):
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


def _uuid_pk():
    return Column(PgUUID(as_uuid=True), primary_key=True)


def _user_fk(name: str, *, ondelete: str = "CASCADE") -> Column:
    return Column(
        PgUUID(as_uuid=True),
        ForeignKey(f"users.id", ondelete=ondelete),
        nullable=False,
    )


class Follow(SQLModel, table=True):
    """Relación "sigue a" entre dos usuarios (unidireccional)."""

    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint(
            "follower_id", "followee_id", name="uq_follows_follower_followee"
        ),
        CheckConstraint("follower_id <> followee_id", name="ck_follows_no_self"),
        Index("ix_follows_followee", "followee_id"),
        Index("ix_follows_follower", "follower_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    follower_id: uuid.UUID = Field(sa_column=_user_fk("follower_id"))
    followee_id: uuid.UUID = Field(sa_column=_user_fk("followee_id"))
    created_at: datetime = Field(sa_column=_datetime(required=True))


class Block(SQLModel, table=True):
    """Bloqueo mutuo: oculta contenido y borra follows a dos sentidos."""

    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("blocker_id", "blocked_id", name="uq_blocks_blocker_blocked"),
        CheckConstraint("blocker_id <> blocked_id", name="ck_blocks_no_self"),
        Index("ix_blocks_blocked", "blocked_id"),
        Index("ix_blocks_blocker", "blocker_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    blocker_id: uuid.UUID = Field(sa_column=_user_fk("blocker_id"))
    blocked_id: uuid.UUID = Field(sa_column=_user_fk("blocked_id"))
    created_at: datetime = Field(sa_column=_datetime(required=True))


class Mute(SQLModel, table=True):
    """Silencio: no oculta mecánicamente, solo filtra el feed (F5)."""

    __tablename__ = "mutes"
    __table_args__ = (
        UniqueConstraint("muter_id", "mutee_id", name="uq_mutes_muter_mutee"),
        CheckConstraint("muter_id <> mutee_id", name="ck_mutes_no_self"),
        Index("ix_mutes_mutee", "mutee_id"),
        Index("ix_mutes_muter", "muter_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    muter_id: uuid.UUID = Field(sa_column=_user_fk("muter_id"))
    mutee_id: uuid.UUID = Field(sa_column=_user_fk("mutee_id"))
    created_at: datetime = Field(sa_column=_datetime(required=True))


class Report(SQLModel, table=True):
    """Reporte de moderación (target polimórfico, sin FK)."""

    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_status", "status"),
        Index("ix_reports_target", "target_type", "target_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    reporter_id: uuid.UUID = Field(sa_column=_user_fk("reporter_id"))
    target_type: ReportTarget = Field(
        sa_column=Column(
            SAEnum(ReportTarget, name="report_target"), nullable=False
        )
    )
    target_id: uuid.UUID = Field(sa_column=Column(PgUUID(as_uuid=True), nullable=False))
    reason: str = Field(sa_column=Column(String(200), nullable=False))
    details: str | None = Field(default=None, sa_column=Column(Text))
    status: ReportStatus = Field(
        default=ReportStatus.OPEN,
        sa_column=Column(SAEnum(ReportStatus, name="report_status"), nullable=False),
    )
    resolved_by: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))
    resolved_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class Activity(SQLModel, table=True):
    """Log append-only de actividad de UX del usuario.

    `visibility` se copia de `privacy_settings.activity_visibility` del
    actor en el momento de creación (ADR-4). Append-only: nunca se edita.
    """

    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_actor_created", "actor_id", text("created_at DESC")),
        Index(
            "ix_activities_public",
            text("created_at DESC"),
            postgresql_where=text("visibility = 'PUBLIC'"),
        ),
        Index("ix_activities_object", "object_type", "object_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=_uuid_pk())
    actor_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    verb: ActivityVerb = Field(
        sa_column=Column(SAEnum(ActivityVerb, name="activity_verb"), nullable=False)
    )
    object_type: ObjectType | None = Field(
        default=None,
        sa_column=Column(SAEnum(ObjectType, name="object_type"), nullable=True),
    )
    object_id: uuid.UUID | None = Field(
        default=None, sa_column=Column(PgUUID(as_uuid=True), nullable=True)
    )
    target_type: str | None = Field(
        default=None, sa_column=Column(String(30), nullable=True)
    )
    target_id: uuid.UUID | None = Field(
        default=None, sa_column=Column(PgUUID(as_uuid=True), nullable=True)
    )
    visibility: Visibility = Field(
        default=Visibility.PUBLIC,
        sa_column=Column(SAEnum(Visibility, name="visibility"), nullable=False),
    )
    created_at: datetime = Field(sa_column=_datetime(required=True))

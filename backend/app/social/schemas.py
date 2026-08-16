"""Esquemas de validación del módulo social."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import Field
from sqlmodel import SQLModel

from app.enums import ActivityVerb, ObjectType, ReportStatus, ReportTarget, Visibility


class UserBrief(SQLModel):
    """Datos mínimos de un usuario en listados sociales."""

    id: str
    username: str
    display_name: str | None = None
    avatar_url: str | None = None


class FollowingUser(UserBrief):
    """Usuario del listado de following/followers, con la fecha del follow."""

    followed_at: datetime


class FollowStatusResponse(SQLModel):
    """¿El usuario autenticado sigue al usuario consultado?"""

    is_following: bool = False


class FollowResponse(SQLModel):
    """Resultado de crear un follow."""

    followee: UserBrief
    created_at: datetime


class UserPage(SQLModel):
    """Página de usuarios (cursor pagination)."""

    items: list[FollowingUser]
    next: str | None = None


class ActivityResponse(SQLModel):
    """Entrada del log de actividad."""

    id: str
    verb: ActivityVerb
    actor: UserBrief | None
    object_type: ObjectType | None = None
    object_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    visibility: Visibility
    created_at: datetime


class ActivityPage(SQLModel):
    """Página de actividades (cursor pagination)."""

    items: list[ActivityResponse]
    next: str | None = None


class ReportCreate(SQLModel):
    """Cuerpo para crear un reporte de moderación."""

    target_type: ReportTarget
    target_id: uuid.UUID
    reason: str = Field(min_length=1, max_length=200)
    details: str | None = Field(default=None, max_length=2000)


class ReportResponse(SQLModel):
    """Reporte creado."""

    id: str
    reporter_id: str
    target_type: ReportTarget
    target_id: str
    reason: str
    details: str | None = None
    status: ReportStatus
    created_at: datetime

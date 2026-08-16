"""Repositorio de persistencia del feed (FASE 5).

Solo lecturas sobre el log de actividades de F4 (no hay tablas nuevas).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.enums import Visibility
from app.social.models import Activity, Follow, Mute

if TYPE_CHECKING:
    CursorAfter = tuple[datetime, uuid.UUID] | None
else:
    CursorAfter = object


class FeedRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_following_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Usuarios a los que sigue `user_id` (sus contenidos van al feed)."""
        stmt = select(Follow.followee_id).where(Follow.follower_id == user_id)
        return [row for row in (await self.db.exec(stmt)).all()]

    async def get_muted_ids(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Usuarios silenciados por `user_id` (excluidos del feed)."""
        stmt = select(Mute.mutee_id).where(Mute.muter_id == user_id)
        return [row for row in (await self.db.exec(stmt)).all()]

    async def list_feed(
        self,
        pool_ids: list[uuid.UUID],
        self_id: uuid.UUID,
        *,
        limit: int,
        after: CursorAfter,
    ) -> list[Activity]:
        """Actividades del pool, ordenadas por fecha desc.

        El autor siempre ve las suyas; el resto solo las no PRIVATE
        (FOLLOWERS es válido porque el feed solo incluye a quien seguimos).
        """
        if not pool_ids:
            return []
        stmt = select(Activity).where(
            Activity.actor_id.in_(pool_ids),
            or_(
                Activity.actor_id == self_id,
                Activity.visibility != Visibility.PRIVATE,
            ),
        )
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where(
                (Activity.created_at, Activity.id) < (created_at, row_id)
            )
        stmt = stmt.order_by(Activity.created_at.desc(), Activity.id.desc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    async def get_profiles_by_user_ids(self, ids: list[uuid.UUID]) -> list:
        from app.profiles.models import Profile

        if not ids:
            return []
        stmt = select(Profile).where(Profile.user_id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_users_by_ids(self, ids: list[uuid.UUID]) -> list:
        from app.auth.models import User

        if not ids:
            return []
        stmt = select(User).where(User.id.in_(ids))
        return (await self.db.exec(stmt)).all()
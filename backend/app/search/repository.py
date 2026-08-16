"""Repositorio de consultas de la búsqueda social (FASE 10).

Solo lecturas con patrones ILIKE normalizados; la lógica de visibilidad
y ranking vive en el servicio.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.models import Book
from app.posts.models import Post
from app.profiles.models import Profile

if TYPE_CHECKING:
    from app.profiles.models import PrivacySetting


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class SearchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search_users(
        self, *, raw: str, normalized: str, pool: int
    ) -> list[tuple[User, Profile | None]]:
        pat_raw = _like_pattern(raw)
        pat_norm = _like_pattern(normalized)
        stmt = (
            select(User, Profile)
            .join(Profile, Profile.user_id == User.id, isouter=True)
            .where(
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                or_(
                    User.username.ilike(pat_raw, escape="\\"),
                    User.username.ilike(pat_norm, escape="\\"),
                    func.unaccent(Profile.display_name).ilike(pat_raw, escape="\\"),
                    func.unaccent(Profile.display_name).ilike(pat_norm, escape="\\"),
                ),
            )
            .order_by(User.username.asc())
            .limit(pool)
        )
        rows = (await self.db.exec(stmt)).all()
        return [(user, profile) for user, profile in rows]

    async def search_books(
        self, *, raw: str, normalized: str, pool: int
    ) -> list[Book]:
        pat_raw = _like_pattern(raw)
        pat_norm = _like_pattern(normalized)
        stmt = (
            select(Book)
            .where(
                or_(
                    Book.normal_title.ilike(pat_norm, escape="\\"),
                    Book.normal_author.ilike(pat_norm, escape="\\"),
                    Book.title.ilike(pat_raw, escape="\\"),
                    Book.author.ilike(pat_raw, escape="\\"),
                )
            )
            .order_by(Book.normal_title.asc())
            .limit(pool)
        )
        return list((await self.db.exec(stmt)).all())

    async def search_posts(
        self, *, raw: str, normalized: str, pool: int
    ) -> list[tuple[Post, User, Profile | None]]:
        pat_raw = _like_pattern(raw)
        pat_norm = _like_pattern(normalized)
        stmt = (
            select(Post, User, Profile)
            .join(User, User.id == Post.author_id)
            .join(Profile, Profile.user_id == User.id, isouter=True)
            .where(
                Post.deleted_at.is_(None),
                User.deleted_at.is_(None),
                User.is_active.is_(True),
                or_(
                    func.unaccent(Post.body).ilike(pat_raw, escape="\\"),
                    func.unaccent(Post.body).ilike(pat_norm, escape="\\"),
                ),
            )
            .order_by(Post.created_at.desc())
            .limit(pool)
        )
        rows = (await self.db.exec(stmt)).all()
        return [(post, user, profile) for post, user, profile in rows]

    # ---------- Visibilidad batch ----------

    async def get_profiles(self, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, Profile]:
        if not user_ids:
            return {}
        stmt = select(Profile).where(Profile.user_id.in_(user_ids))
        return {
            profile.user_id: profile
            for profile in (await self.db.exec(stmt)).all()
        }

    async def get_privacy_settings(
        self, user_ids: set[uuid.UUID]
    ) -> dict[uuid.UUID, "PrivacySetting"]:
        if not user_ids:
            return {}
        from app.profiles.models import PrivacySetting

        stmt = select(PrivacySetting).where(
            PrivacySetting.user_id.in_(user_ids)
        )
        return {
            setting.user_id: setting
            for setting in (await self.db.exec(stmt)).all()
        }

    async def followed_ids(
        self, viewer_id: uuid.UUID, user_ids: set[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not user_ids:
            return set()
        from app.social.models import Follow

        stmt = select(Follow.followee_id).where(
            Follow.follower_id == viewer_id,
            Follow.followee_id.in_(user_ids),
        )
        return {row for row in (await self.db.exec(stmt)).all()}

    async def blocked_ids(
        self, viewer_id: uuid.UUID, user_ids: set[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not user_ids:
            return set()
        from app.social.models import Block

        stmt = select(Block).where(
            or_(
                (Block.blocker_id == viewer_id) & Block.blocked_id.in_(user_ids),
                (Block.blocker_id.in_(user_ids)) & (Block.blocked_id == viewer_id),
            )
        )
        rows = (await self.db.exec(stmt)).all()
        related = {b.blocker_id for b in rows} | {b.blocked_id for b in rows}
        return related & user_ids

    async def muted_ids(
        self, viewer_id: uuid.UUID, user_ids: set[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not user_ids:
            return set()
        from app.social.models import Mute

        stmt = select(Mute.mutee_id).where(
            Mute.muter_id == viewer_id,
            Mute.mutee_id.in_(user_ids),
        )
        return {row for row in (await self.db.exec(stmt)).all()}
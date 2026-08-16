"""Repositorio de consultas del módulo de recomendaciones (FASE 11).

Solo lecturas sobre ratings/reviews (F3), library (F2) y posts (F6);
sin lógica de negocio.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.models import Book
from app.posts.models import Comment, Post, PostLike
from app.profiles.models import Profile
from app.reviews.models import Rating
from app.shelves.models import UserBook

if TYPE_CHECKING:
    pass


class RecommendationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_high_rated_books(
        self, user_id: uuid.UUID, min_score: int = 4
    ) -> list[tuple[int, str, str]]:
        """(book_id, author, normal_author) de libros valorados >= min_score."""
        stmt = (
            select(Rating.book_id, Book.author, Book.normal_author)
            .join(Book, Book.id == Rating.book_id)
            .where(Rating.user_id == user_id, Rating.score >= min_score)
        )
        rows = (await self.db.exec(stmt)).all()
        return [(book_id, author, normal_author) for book_id, author, normal_author in rows]

    async def get_user_book_ids(self, user_id: uuid.UUID) -> set[int]:
        stmt = select(UserBook.book_id).where(UserBook.user_id == user_id)
        return {row for row in (await self.db.exec(stmt)).all()}

    async def get_rated_book_ids(self, user_id: uuid.UUID) -> set[int]:
        stmt = select(Rating.book_id).where(Rating.user_id == user_id)
        return {row for row in (await self.db.exec(stmt)).all()}

    async def get_books_by_authors(
        self, authors: set[str], exclude: set[int], limit: int
    ) -> list[Book]:
        if not authors:
            return []
        stmt = (
            select(Book)
            .where(
                Book.normal_author.in_(authors),
                Book.id.not_in(exclude),
            )
            .order_by(Book.rating_count.desc(), Book.rating_avg.desc().nullslast())
            .limit(limit)
        )
        return list((await self.db.exec(stmt)).all())

    async def get_similar_users(
        self, seed_book_ids: list[int], exclude_user_id: uuid.UUID, limit: int = 30
    ) -> list[tuple[uuid.UUID, int]]:
        """Usuarios que valoraron >= 4 los libros semilla, por nº de coincidencias."""
        if not seed_book_ids:
            return []
        stmt = (
            select(Rating.user_id, func.count(Rating.id))
            .where(
                Rating.book_id.in_(seed_book_ids),
                Rating.score >= 4,
                Rating.user_id != exclude_user_id,
            )
            .group_by(Rating.user_id)
            .order_by(func.count(Rating.id).desc())
            .limit(limit)
        )
        rows = (await self.db.exec(stmt)).all()
        return [(user_id, count) for user_id, count in rows]

    async def get_books_rated_by_users(
        self,
        similar_user_ids: list[uuid.UUID],
        exclude_book_ids: set[int],
        limit: int,
    ) -> list[tuple[int, int, float]]:
        """(book_id, nº usuarios similares, avg score) con score >= 4."""
        if not similar_user_ids:
            return []
        stmt = (
            select(
                Rating.book_id,
                func.count(Rating.user_id),
                func.avg(Rating.score),
            )
            .where(
                Rating.user_id.in_(similar_user_ids),
                Rating.score >= 4,
                Rating.book_id.not_in(exclude_book_ids),
            )
            .group_by(Rating.book_id)
            .order_by(func.count(Rating.user_id).desc(), func.avg(Rating.score).desc())
            .limit(limit)
        )
        rows = (await self.db.exec(stmt)).all()
        return [(book_id, count, float(avg)) for book_id, count, avg in rows]

    async def get_popular_books(self, limit: int) -> list[Book]:
        stmt = (
            select(Book)
            .where(Book.rating_count > 0)
            .order_by(
                Book.rating_count.desc(),
                Book.rating_avg.desc().nullslast(),
            )
            .limit(limit)
        )
        return list((await self.db.exec(stmt)).all())

    async def list_popular_post_candidates(
        self, pool: int
    ) -> list[tuple[Post, User, Profile | None, int, int]]:
        like_ct = (
            select(PostLike.post_id, func.count(PostLike.id).label("n"))
            .group_by(PostLike.post_id)
            .subquery()
        )
        comment_ct = (
            select(Comment.post_id, func.count(Comment.id).label("n"))
            .where(Comment.deleted_at.is_(None))
            .group_by(Comment.post_id)
            .subquery()
        )
        engagement = (
            func.coalesce(like_ct.c.n, 0) * 2 + func.coalesce(comment_ct.c.n, 0) * 3
        )
        stmt = (
            select(Post, User, Profile, like_ct.c.n, comment_ct.c.n)
            .join(User, User.id == Post.author_id)
            .join(Profile, Profile.user_id == User.id, isouter=True)
            .outerjoin(like_ct, like_ct.c.post_id == Post.id)
            .outerjoin(comment_ct, comment_ct.c.post_id == Post.id)
            .where(
                Post.deleted_at.is_(None),
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .order_by(engagement.desc(), Post.created_at.desc())
            .limit(pool)
        )
        rows = (await self.db.exec(stmt)).all()
        return [
            (post, user, profile, int(like_ct or 0), int(comment_ct or 0))
            for post, user, profile, like_ct, comment_ct in rows
        ]

    async def get_books_by_ids(self, ids: set[int]) -> dict[int, Book]:
        if not ids:
            return {}
        stmt = select(Book).where(Book.id.in_(ids))
        return {book.id: book for book in (await self.db.exec(stmt)).all()}

    # ---------- Visibilidad batch ----------

    async def get_profiles(self, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, Profile]:
        if not user_ids:
            return {}
        stmt = select(Profile).where(Profile.user_id.in_(user_ids))
        return {p.user_id: p for p in (await self.db.exec(stmt)).all()}

    async def followed_ids(
        self, viewer_id: uuid.UUID, user_ids: set[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not user_ids:
            return set()
        from app.social.models import Follow

        stmt = select(Follow.followee_id).where(
            Follow.follower_id == viewer_id, Follow.followee_id.in_(user_ids)
        )
        return {row for row in (await self.db.exec(stmt)).all()}

    async def blocked_ids(
        self, viewer_id: uuid.UUID, user_ids: set[uuid.UUID]
    ) -> set[uuid.UUID]:
        if not user_ids:
            return set()
        from sqlalchemy import or_

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
            Mute.muter_id == viewer_id, Mute.mutee_id.in_(user_ids)
        )
        return {row for row in (await self.db.exec(stmt)).all()}
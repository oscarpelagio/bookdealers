"""Repositorio de persistencia del módulo reviews.

Solo operaciones de base de datos; sin lógica de negocio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import and_, func, or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.enums import Visibility
from app.models import Book
from app.reviews.models import Rating, Review, ReviewLike
from app.shelves.models import UserBook
from app.social.models import Block, Follow

if TYPE_CHECKING:
    CursorAfter = tuple[datetime, uuid.UUID] | None
else:
    CursorAfter = object


class ReviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Book / UserBook ----------

    async def get_book(self, book_id: int) -> Book | None:
        return await self.db.get(Book, book_id)

    async def get_user_book(self, user_id: uuid.UUID, book_id: int) -> UserBook | None:
        stmt = select(UserBook).where(
            UserBook.user_id == user_id, UserBook.book_id == book_id
        )
        return (await self.db.exec(stmt)).first()

    # ---------- Rating ----------

    async def get_rating(self, user_id: uuid.UUID, book_id: int) -> Rating | None:
        stmt = select(Rating).where(
            Rating.user_id == user_id, Rating.book_id == book_id
        )
        return (await self.db.exec(stmt)).first()

    async def create_rating(self, user_id: uuid.UUID, book_id: int, score: int) -> Rating:
        rating = Rating(user_id=user_id, book_id=book_id, score=score)
        self.db.add(rating)
        await self.db.flush()
        return rating

    async def update_rating(self, rating: Rating, score: int) -> Rating:
        rating.score = score
        rating.updated_at = datetime.now()
        return rating

    # ---------- Review ----------

    async def get_active_review(self, user_id: uuid.UUID, book_id: int) -> Review | None:
        stmt = select(Review).where(
            Review.user_id == user_id,
            Review.book_id == book_id,
            Review.deleted_at.is_(None),
        )
        return (await self.db.exec(stmt)).first()

    async def get_review_by_id(self, review_id: uuid.UUID) -> Review | None:
        return await self.db.get(Review, review_id)

    async def create_review(
        self,
        *,
        user_id: uuid.UUID,
        book_id: int,
        rating_id: uuid.UUID | None,
        title: str | None,
        body: str | None,
        spoiler: bool,
        language: str | None,
        visibility: Visibility,
    ) -> Review:
        review = Review(
            user_id=user_id,
            book_id=book_id,
            rating_id=rating_id,
            title=title,
            body=body,
            spoiler=spoiler,
            language=language,
            visibility=visibility,
        )
        self.db.add(review)
        await self.db.flush()
        return review

    async def soft_delete(self, review: Review, deleted_at: datetime) -> None:
        review.deleted_at = deleted_at
        review.updated_at = datetime.now()

    async def list_active_reviews_by_book(
        self,
        book_id: int,
        *,
        limit: int,
        after: CursorAfter,
        viewer_id: uuid.UUID | None = None,
    ) -> list[Review]:
        """Reviews activas del libro visibles para el espectador (ADR-4).

        Filtra por la visibilidad snapshot de cada review (`visibility`),
        por la relación de follow (tier FOLLOWERS) y por bloqueos en
        cualquiera de las dos direcciones. Para anónimos solo PUBLIC (y se
        excluyen los autores con `block_anonymous`).
        """
        stmt = select(Review).where(
            Review.book_id == book_id, Review.deleted_at.is_(None)
        )
        if viewer_id is not None:
            blocks_by_viewer = select(Block.blocked_id).where(
                Block.blocker_id == viewer_id
            )
            blocks_on_viewer = select(Block.blocker_id).where(
                Block.blocked_id == viewer_id
            )
            followed = select(Follow.followee_id).where(
                Follow.follower_id == viewer_id
            )
            stmt = stmt.where(
                Review.user_id.not_in(blocks_by_viewer),
                Review.user_id.not_in(blocks_on_viewer),
                or_(
                    Review.user_id == viewer_id,
                    Review.visibility == Visibility.PUBLIC,
                    and_(
                        Review.visibility == Visibility.FOLLOWERS,
                        Review.user_id.in_(followed),
                    ),
                ),
            )
        else:
            from app.profiles.models import PrivacySetting

            anon_blocked = select(PrivacySetting.user_id).where(
                PrivacySetting.block_anonymous.is_(True)
            )
            stmt = stmt.where(
                Review.visibility == Visibility.PUBLIC,
                Review.user_id.not_in(anon_blocked),
            )
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where(
                (Review.created_at, Review.id)
                < (created_at, row_id)
            )
        stmt = stmt.order_by(Review.created_at.desc(), Review.id.desc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    async def list_active_reviews_by_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        after: CursorAfter,
        allowed: list[Visibility] | None = None,
    ) -> list[Review]:
        """Reviews activas del usuario.

        `allowed` es `None` (todas) o la lista de visibilidades aceptadas;
        si la lista está vacía no se devuelve nada (bloqueado/privado).
        """
        if allowed == []:
            return []
        stmt = select(Review).where(
            Review.user_id == user_id, Review.deleted_at.is_(None)
        )
        if allowed is not None:
            stmt = stmt.where(Review.visibility.in_(allowed))
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where(
                (Review.created_at, Review.id)
                < (created_at, row_id)
            )
        stmt = stmt.order_by(Review.created_at.desc(), Review.id.desc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    # ---------- ReviewLike ----------

    async def get_like(self, user_id: uuid.UUID, review_id: uuid.UUID) -> ReviewLike | None:
        stmt = select(ReviewLike).where(
            ReviewLike.user_id == user_id, ReviewLike.review_id == review_id
        )
        return (await self.db.exec(stmt)).first()

    async def create_like(self, user_id: uuid.UUID, review_id: uuid.UUID) -> ReviewLike:
        like = ReviewLike(user_id=user_id, review_id=review_id)
        self.db.add(like)
        return like

    async def delete_like(self, like: ReviewLike) -> None:
        await self.db.delete(like)

    async def count_likes(self, review_id: uuid.UUID) -> int:
        stmt = select(func.count(ReviewLike.id)).where(
            ReviewLike.review_id == review_id
        )
        return (await self.db.exec(stmt)).one()

    # ---------- Users ----------

    async def get_user_by_handle(self, handle: str) -> User | None:
        stmt = select(User).where(User.username == handle)
        return (await self.db.exec(stmt)).first()

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    # ---------- Relaciones sociales para visibilidad ----------

    async def get_follow(
        self, follower_id: uuid.UUID, followee_id: uuid.UUID
    ) -> Follow | None:
        stmt = select(Follow).where(
            Follow.follower_id == follower_id, Follow.followee_id == followee_id
        )
        return (await self.db.exec(stmt)).first()

    async def get_block_relation(self, a: uuid.UUID, b: uuid.UUID) -> Block | None:
        stmt = select(Block).where(
            or_(
                (Block.blocker_id == a) & (Block.blocked_id == b),
                (Block.blocker_id == b) & (Block.blocked_id == a),
            )
        )
        return (await self.db.exec(stmt)).first()

    async def get_users_by_ids(self, ids: list[uuid.UUID]) -> list[User]:
        if not ids:
            return []
        stmt = select(User).where(User.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    # ---------- Agregación para respuestas (evita N+1) ----------

    async def get_profiles_by_user_ids(self, ids: list[uuid.UUID]) -> list:
        from app.profiles.models import Profile

        if not ids:
            return []
        stmt = select(Profile).where(Profile.user_id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_privacy_by_user_ids(self, ids: list[uuid.UUID]) -> list:
        from app.profiles.models import PrivacySetting

        if not ids:
            return []
        stmt = select(PrivacySetting).where(PrivacySetting.user_id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_books_by_ids(self, ids: list[int]) -> list[Book]:
        if not ids:
            return []
        stmt = select(Book).where(Book.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_ratings_by_ids(self, ids: list[uuid.UUID]) -> list[Rating]:
        if not ids:
            return []
        stmt = select(Rating).where(Rating.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def count_likes_by_review_ids(
        self, review_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not review_ids:
            return {}
        stmt = (
            select(ReviewLike.review_id, func.count(ReviewLike.id))
            .where(ReviewLike.review_id.in_(review_ids))
            .group_by(ReviewLike.review_id)
        )
        rows = (await self.db.exec(stmt)).all()
        return {review_id: count for review_id, count in rows}

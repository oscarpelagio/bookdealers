"""Lógica de dominio del módulo reviews.

Reglas (documento FASE 1 §1.6 y FASE 3):
- Única review ACTIVA por (user, book). Soft delete para permitir re-review
  (ADR-8); el rating sobrevive al borrado de la review.
- Escribir una review requiere que el libro esté en la librería (UserBook)
  y un `score` 1..5 obligatorio (regla de producto).
- Los contadores de `books` (rating_avg/count, review_count) se actualizan
  vía eventos `rating_changed`/`review_changed` (ADR-9).
- La visibilidad se snapshotea en `reviews.visibility` al crear (ADR-4, igual
  que activities): el autor siempre ve; PRIVATE solo autor; FOLLOWERS
  autor+seguidores; bloqueos y `block_anonymous` se evalúan en lectura.
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.events import event_bus
from app.core.pagination import decode_cursor, encode_cursor
from app.core.time import utcnow
from app.core.visibility import is_visible
from app.enums import Visibility
from app.models import Book
from app.reviews import events
from app.reviews.exceptions import (
    CannotLikeOwnReviewError,
    RatingRequiredError,
    ReviewAlreadyExistsError,
    ReviewNotFoundError,
    ReviewPrivateError,
    UserBookRequiredError,
)
from app.reviews.models import Rating, Review, ReviewLike
from app.reviews.repository import ReviewRepository
from app.reviews.schemas import (
    AuthorBrief,
    MyReviewResponse,
    ReviewBookBrief,
    ReviewLikeResponse,
    ReviewPage,
    ReviewResponse,
)
from app.shelves.exceptions import BookNotFoundError


class ReviewService:
    def __init__(self, repo: ReviewRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    # ---------- Crear / actualizar / borrar ----------

    async def create_review(
        self,
        user,
        book_id: int,
        *,
        score: int,
        title: str | None,
        body: str | None,
        spoiler: bool,
        language: str | None,
    ) -> ReviewResponse:
        book = await self.repo.get_book(book_id)
        if book is None:
            raise BookNotFoundError()

        user_book = await self.repo.get_user_book(user.id, book_id)
        if user_book is None:
            raise UserBookRequiredError()

        if await self.repo.get_active_review(user.id, book_id) is not None:
            raise ReviewAlreadyExistsError()

        rating = await self.repo.get_rating(user.id, book_id)
        if rating is None:
            rating = await self.repo.create_rating(user.id, book_id, score)

        review = await self.repo.create_review(
            user_id=user.id,
            book_id=book_id,
            rating_id=rating.id,
            title=title,
            body=body,
            spoiler=spoiler,
            language=language,
            visibility=await self._snapshot_visibility(user.id),
        )

        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ReviewAlreadyExistsError()

        await self.db.refresh(review)
        await event_bus.publish(events.rating_changed(book_id))
        await event_bus.publish(events.review_changed(book_id))
        return await self._single_response(review, user, book, rating)

    async def update_review(
        self, user, book_id: int, *, fields: dict
    ) -> ReviewResponse:
        review = await self.repo.get_active_review(user.id, book_id)
        if review is None:
            raise ReviewNotFoundError()

        book = await self.repo.get_book(book_id)
        fields = dict(fields)
        score = fields.pop("score", None)
        if score is not None:
            rating = await self.repo.get_rating(user.id, book_id)
            if rating is not None:
                rating = await self.repo.update_rating(rating, score)
            else:
                rating = await self.repo.create_rating(user.id, book_id, score)

        for field in ("title", "body", "spoiler", "language"):
            if field in fields:
                setattr(review, field, fields[field])
        review.updated_at = utcnow()

        await self.db.commit()
        await self.db.refresh(review)

        rating = await self.repo.get_rating(user.id, book_id)
        if score is not None:
            await event_bus.publish(events.rating_changed(book_id))
        await event_bus.publish(events.review_changed(book_id))
        return await self._single_response(review, user, book, rating)

    async def delete_review(self, user, book_id: int) -> None:
        review = await self.repo.get_active_review(user.id, book_id)
        if review is None:
            raise ReviewNotFoundError()

        # El rating sobrevive como fila (rating_count se mantiene), pero la
        # review deja de referenciarlo (ix_reviews_rating_id es UNIQUE): así un
        # re-review posterior puede reutilizar el mismo rating sin colisión.
        review.rating_id = None
        await self.repo.soft_delete(review, utcnow())
        await self.db.commit()
        await event_bus.publish(events.review_changed(book_id))

    # ---------- Lecturas ----------

    async def get_my_review(self, user, book_id: int) -> ReviewResponse | None:
        review = await self.repo.get_active_review(user.id, book_id)
        if review is None:
            return None
        book = await self.repo.get_book(book_id)
        rating = await self.repo.get_rating(user.id, book_id)
        return await self._single_response(review, user, book, rating)

    async def get_public_review(self, review_id: uuid.UUID, viewer) -> ReviewResponse:
        review = await self._visible_review(review_id, viewer)
        author = await self.repo.get_user(review.user_id)
        book = await self.repo.get_book(review.book_id)
        rating = await self.repo.get_rating(review.user_id, review.book_id)
        return await self._single_response(review, author, book, rating)

    async def list_book_reviews(
        self, book_id: int, viewer, *, cursor: str | None, limit: int
    ) -> ReviewPage:
        if await self.repo.get_book(book_id) is None:
            raise BookNotFoundError()
        after = decode_cursor(cursor)
        viewer_id = viewer.id if viewer else None
        reviews = await self.repo.list_active_reviews_by_book(
            book_id, limit=limit + 1, after=after, viewer_id=viewer_id
        )
        return await self._paginate(reviews, viewer, limit)

    async def list_user_reviews(
        self, handle: str, viewer, *, cursor: str | None, limit: int
    ) -> ReviewPage:
        author = await self.repo.get_user_by_handle(handle)
        if author is None:
            raise ReviewNotFoundError()

        viewer_id = viewer.id if viewer else None
        allowed: list[Visibility] | None
        if viewer_id is not None and viewer_id == author.id:
            allowed = None
        else:
            allowed = [Visibility.PUBLIC]
            if viewer_id is not None:
                if (
                    await self.repo.get_block_relation(viewer_id, author.id)
                ) is not None:
                    allowed = []
                elif (
                    await self.repo.get_follow(viewer_id, author.id)
                ) is not None:
                    allowed.append(Visibility.FOLLOWERS)
            else:
                privacy = (
                    await self.repo.get_privacy_by_user_ids([author.id]) or [None]
                )[0]
                if privacy is not None and privacy.block_anonymous:
                    allowed = []

        after = decode_cursor(cursor)
        reviews = await self.repo.list_active_reviews_by_user(
            author.id, allowed=allowed, limit=limit + 1, after=after
        )
        return await self._paginate(reviews, viewer, limit)

    async def list_my_reviews(
        self, user, *, cursor: str | None, limit: int
    ) -> ReviewPage:
        after = decode_cursor(cursor)
        reviews = await self.repo.list_active_reviews_by_user(
            user.id, limit=limit + 1, after=after
        )
        return await self._paginate(reviews, user, limit)

    # ---------- Likes ----------

    async def like_review(self, user, review_id: uuid.UUID) -> ReviewLikeResponse:
        review = await self._visible_review(review_id, user)
        if review.user_id == user.id:
            raise CannotLikeOwnReviewError()

        like = await self.repo.get_like(user.id, review_id)
        created = False
        if like is None:
            like = await self.repo.create_like(user.id, review_id)
            created = True
            try:
                await self.db.commit()
            except IntegrityError:
                # Carrera: otro request creó el like. Idempotente, no 500.
                await self.db.rollback()
                like = await self.repo.get_like(user.id, review_id)
                created = False
                if like is None:
                    raise
            await self.db.refresh(like)
            if created:
                await event_bus.publish(
                    events.review_liked(str(review_id), str(user.id))
                )
        return ReviewLikeResponse(
            id=str(like.id),
            review_id=str(review_id),
            created_at=like.created_at,
        )

    async def unlike_review(self, user, review_id: uuid.UUID) -> None:
        like = await self.repo.get_like(user.id, review_id)
        if like is None:
            return
        await self.repo.delete_like(like)
        await self.db.commit()
        await event_bus.publish(events.review_unliked(str(review_id), str(user.id)))

    # ---------- Helpers ----------

    async def _visible_review(self, review_id: uuid.UUID, viewer) -> Review:
        review = await self.repo.get_review_by_id(review_id)
        if review is None or review.deleted_at is not None:
            raise ReviewNotFoundError()
        author = await self.repo.get_user(review.user_id)
        if author is None or not author.is_active or author.deleted_at is not None:
            raise ReviewNotFoundError()
        if viewer is not None and viewer.id == review.user_id:
            return review

        viewer_id = viewer.id if viewer else None
        is_blocked = False
        if viewer_id is not None:
            is_blocked = (
                await self.repo.get_block_relation(viewer_id, review.user_id)
            ) is not None
        if is_blocked:
            raise ReviewNotFoundError()

        is_follower = False
        if viewer_id is not None:
            is_follower = (
                await self.repo.get_follow(viewer_id, review.user_id)
            ) is not None
        elif viewer_id is None:
            privacy = (
                await self.repo.get_privacy_by_user_ids([review.user_id]) or [None]
            )[0]
            if privacy is not None and privacy.block_anonymous:
                raise ReviewPrivateError()

        visible = is_visible(
            review.visibility,
            viewer_id=viewer_id,
            author_id=review.user_id,
            is_follower=is_follower,
            is_blocked=False,
            author_active=author.is_active and author.deleted_at is None,
        )
        if not visible:
            raise ReviewPrivateError()
        return review

    async def _snapshot_visibility(self, user_id: uuid.UUID) -> Visibility:
        """Snapshotea la visibilidad de reviews del autor (ADR-4)."""
        privacy = (
            await self.repo.get_privacy_by_user_ids([user_id]) or [None]
        )[0]
        return privacy.reviews_visibility if privacy else Visibility.PUBLIC

    async def _paginate(self, reviews: list[Review], viewer, limit: int) -> ReviewPage:
        has_more = len(reviews) > limit
        page = reviews[:limit]
        next_cursor = None
        if has_more and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        items = await self._responses(page, viewer)
        return ReviewPage(items=items, next=next_cursor)

    async def _responses(
        self, reviews: list[Review], viewer
    ) -> list[ReviewResponse]:
        if not reviews:
            return []

        user_ids = list({r.user_id for r in reviews})
        book_ids = list({r.book_id for r in reviews})
        rating_ids = [r.rating_id for r in reviews if r.rating_id]

        users = {u.id: u for u in await self.repo.get_users_by_ids(user_ids)}
        profiles = {
            p.user_id: p for p in await self.repo.get_profiles_by_user_ids(user_ids)
        }
        books = {b.id: b for b in await self.repo.get_books_by_ids(book_ids)}
        ratings = {
            r.id: r for r in await self.repo.get_ratings_by_ids(rating_ids or [])
        }
        likes = await self.repo.count_likes_by_review_ids([r.id for r in reviews])

        viewer_id = viewer.id if viewer else None
        result: list[ReviewResponse] = []
        for review in reviews:
            author = users.get(review.user_id)
            if author is None:
                continue
            profile = profiles.get(review.user_id)
            book = books.get(review.book_id)
            if book is None:
                continue
            rating = ratings.get(review.rating_id)
            result.append(
                ReviewResponse(
                    id=str(review.id),
                    book_id=review.book_id,
                    title=review.title,
                    body=review.body,
                    spoiler=review.spoiler,
                    language=review.language,
                    score=rating.score if rating else None,
                    like_count=likes.get(review.id, 0),
                    created_at=review.created_at,
                    updated_at=review.updated_at,
                    author=AuthorBrief(
                        id=str(author.id),
                        username=author.username,
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                    ),
                    book=ReviewBookBrief(
                        id=book.id,
                        title=book.title,
                        author=book.author,
                        thumbnail=book.thumbnail,
                    ),
                )
            )
        return result

    async def _single_response(
        self, review: Review, author, book: Book, rating: Rating | None
    ) -> ReviewResponse:
        profile = (
            await self.repo.get_profiles_by_user_ids([author.id]) or [None]
        )[0]
        likes = await self.repo.count_likes_by_review_ids([review.id])
        return ReviewResponse(
            id=str(review.id),
            book_id=review.book_id,
            title=review.title,
            body=review.body,
            spoiler=review.spoiler,
            language=review.language,
            score=rating.score if rating else None,
            like_count=likes.get(review.id, 0),
            created_at=review.created_at,
            updated_at=review.updated_at,
            author=AuthorBrief(
                id=str(author.id),
                username=author.username,
                display_name=profile.display_name if profile else None,
                avatar_url=profile.avatar_url if profile else None,
            ),
            book=ReviewBookBrief(
                id=book.id,
                title=book.title,
                author=book.author,
                thumbnail=book.thumbnail,
            ),
        )

    async def my_review_response(
        self, user, book_id: int
    ) -> MyReviewResponse | None:
        review = await self.repo.get_active_review(user.id, book_id)
        if review is None:
            return None
        base = await self.get_my_review(user, book_id)
        if base is None:
            return None
        data = base.model_dump()
        data["visibility"] = review.visibility
        return MyReviewResponse(**data)

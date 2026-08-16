"""Lógica de negocio del módulo de recomendaciones (FASE 11)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from app.core.visibility import is_visible
from app.recommendations.repository import RecommendationRepository
from app.recommendations.schemas import PopularPost, RecommendationItem
from app.search.schemas import BookSearchResult
from app.social.schemas import UserBrief

if TYPE_CHECKING:
    from app.auth.models import User


def _book_result(book) -> BookSearchResult:
    return BookSearchResult(
        id=book.id,
        title=book.title,
        author=book.author,
        thumbnail=book.thumbnail,
        publisher=book.publisher,
        publisher_date=book.publisher_date,
        language=book.language,
        page_count=book.page_count,
        categories=book.categories,
    )


class RecommendationService:
    def __init__(self, repository: RecommendationRepository) -> None:
        self.repo = repository

    # ---------- Recomendaciones ----------

    async def get_recommendations(
        self, viewer: "User | None", limit: int
    ) -> list[RecommendationItem]:
        if viewer is None:
            return await self._popular_only(limit)

        user_id = viewer.id
        seed = await self.repo.get_high_rated_books(user_id)
        exclude = (await self.repo.get_user_book_ids(user_id)) | (
            await self.repo.get_rated_book_ids(user_id)
        )
        if not seed:
            return await self._popular_only(limit)

        # 1) Autor-based: otros libros de los autores que más me gustan.
        authors = {normal_author for _, _, normal_author in seed if normal_author}
        author_books = await self.repo.get_books_by_authors(authors, exclude, limit)
        items: dict[int, tuple[float, str]] = {}
        for book in author_books:
            items[book.id] = (float(book.rating_avg or 0), "author")

        # 2) Colaborativo: usuarios afines y sus otros libros bien valorados.
        seed_ids = [book_id for book_id, _, _ in seed]
        similar = await self.repo.get_similar_users(seed_ids, user_id)
        similar_ids = [s_user_id for s_user_id, _ in similar]
        collab = await self.repo.get_books_rated_by_users(
            similar_ids, set(exclude) | set(items.keys()), limit
        )
        for book_id, count, avg in collab:
            items[book_id] = (count + avg, "collaborative")

        # 3) Relleno con populares si faltan.
        if len(items) < limit:
            popular = await self.repo.get_popular_books(limit - len(items))
            for book in popular:
                if book.id in items or book.id in exclude:
                    continue
                items[book.id] = (float(book.rating_avg or 0), "popular")
                if len(items) >= limit:
                    break

        ordered = sorted(items.items(), key=lambda kv: -kv[1][0])
        books = await self.repo.get_books_by_ids({book_id for book_id, _ in ordered})
        result: list[RecommendationItem] = []
        for book_id, (score, source) in ordered:
            book = books.get(book_id)
            if book is None:
                continue
            result.append(
                RecommendationItem(
                    book=_book_result(book),
                    source=source,
                    score=round(score, 2),
                )
            )
            if len(result) >= limit:
                break
        return result

    async def _popular_only(self, limit: int) -> list[RecommendationItem]:
        books = await self.repo.get_popular_books(limit)
        return [
            RecommendationItem(
                book=_book_result(book),
                source="popular",
                score=float(book.rating_avg or 0),
            )
            for book in books
        ]

    # ---------- Feed popular ----------

    async def get_popular_posts(
        self, viewer: "User | None", limit: int
    ) -> list[PopularPost]:
        pool = min(max(limit * 4, 20), 200)
        candidates = await self.repo.list_popular_post_candidates(pool)
        if not candidates:
            return []

        viewer_id = viewer.id if viewer is not None else None
        author_ids = {post.author_id for post, _, _, _, _ in candidates}
        profiles = await self.repo.get_profiles(author_ids)
        followed: set = set()
        blocked: set = set()
        muted: set = set()
        if viewer_id is not None:
            followed = await self.repo.followed_ids(viewer_id, author_ids)
            blocked = await self.repo.blocked_ids(viewer_id, author_ids)
            muted = await self.repo.muted_ids(viewer_id, author_ids)

        result: list[PopularPost] = []
        for post, author, _profile, like_count, comment_count in candidates:
            if author.id != viewer_id and author.id in muted:
                continue
            visible = is_visible(
                section=post.visibility,
                viewer_id=viewer_id,
                author_id=author.id,
                is_follower=author.id in followed,
                is_blocked=author.id in blocked,
                author_active=author.is_active and author.deleted_at is None,
            )
            if not visible:
                continue
            profile = profiles.get(author.id)
            result.append(
                PopularPost(
                    id=str(post.id),
                    body=post.body,
                    visibility=post.visibility,
                    like_count=like_count,
                    comment_count=comment_count,
                    created_at=post.created_at,
                    author=UserBrief(
                        id=str(author.id),
                        username=author.username,
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                    ),
                )
            )
            if len(result) >= limit:
                break
        return result
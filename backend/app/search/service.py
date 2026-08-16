"""Lógica de negocio de la búsqueda social (FASE 10).

Ranking, normalización de tildes y filtros de visibilidad:
- `search_users`: solo usuarios activos; privacidad de perfil y bloqueos
  (batch) según ADR-4; anónimos sin `block_anonymous`.
- `search_books`: catálogo local, sin visibilidad.
- `search_posts`: solo posts visibles al espectador (PRIVATE excluidos);
  excluye autores bloqueados o silenciados.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.visibility import is_visible
from app.enums import Visibility
from app.search.repository import SearchRepository
from app.search.schemas import BookSearchResult, PostSearchResult, UserSearchResult
from app.utils import NormalizationUtils

if TYPE_CHECKING:
    from app.auth.models import User


def _normalize(value: str) -> str:
    return NormalizationUtils.normalize_text(value)


def _score(prefixes: list[str], haystacks: list[str]) -> int:
    """Ranking simple: prefijo > contiene. Devuelve mayor puntuación."""
    best = 0
    for prefix in prefixes:
        for haystack in haystacks:
            if haystack == prefix:
                best = max(best, 3)
            elif haystack.startswith(prefix):
                best = max(best, 2)
            elif prefix in haystack:
                best = max(best, 1)
    return best


class SearchService:
    def __init__(self, repository: SearchRepository) -> None:
        self.repo = repository

    async def search_users(
        self, *, query: str, viewer: "User | None", limit: int
    ) -> list[UserSearchResult]:
        qn = _normalize(query)
        if not qn:
            return []
        pool = self._pool_size(limit)
        candidates = await self.repo.search_users(
            raw=query, normalized=qn, pool=pool
        )
        if not candidates:
            return []

        viewer_id = viewer.id if viewer is not None else None
        user_ids = {user.id for user, _ in candidates}
        profiles = await self.repo.get_profiles(user_ids)
        privacy_map = await self.repo.get_privacy_settings(user_ids)
        followed: set = set()
        blocked: set = set()
        if viewer_id is not None:
            followed = await self.repo.followed_ids(viewer_id, user_ids)
            blocked = await self.repo.blocked_ids(viewer_id, user_ids)

        results: list[tuple[int, UserSearchResult]] = []
        for user, _profile in candidates:
            if user.id == viewer_id:
                is_visible_result = True
            else:
                privacy = privacy_map.get(user.id)
                if viewer_id is None and privacy is not None and privacy.block_anonymous:
                    is_visible_result = False
                else:
                    is_visible_result = is_visible(
                        section=privacy.profile_visibility if privacy else Visibility.PUBLIC,
                        viewer_id=viewer_id,
                        author_id=user.id,
                        is_follower=user.id in followed,
                        is_blocked=user.id in blocked,
                        author_active=user.is_active and user.deleted_at is None,
                    )
            if not is_visible_result:
                continue

            profile = profiles.get(user.id)
            display_name = profile.display_name if profile else None
            result = UserSearchResult(
                id=str(user.id),
                username=user.username,
                display_name=display_name,
                avatar_url=profile.avatar_url if profile else None,
            )
            score = _score(
                [qn],
                [
                    _normalize(user.username),
                    _normalize(display_name or ""),
                ],
            )
            if score == 0:
                continue
            results.append((score, result))

        results.sort(key=lambda pair: (-pair[0], pair[1].username.lower()))
        return [r for _, r in results[:limit]]

    async def search_books(
        self, *, query: str, limit: int
    ) -> list[BookSearchResult]:
        qn = _normalize(query)
        if not qn:
            return []
        pool = self._pool_size(limit)
        books = await self.repo.search_books(raw=query, normalized=qn, pool=pool)
        if not books:
            return []

        scored: list[tuple[int, BookSearchResult]] = []
        for book in books:
            score = _score(
                [qn],
                [
                    _normalize(book.title),
                    _normalize(book.author),
                ],
            )
            if score == 0:
                continue
            scored.append(
                (
                    score,
                    BookSearchResult(
                        id=book.id,
                        title=book.title,
                        author=book.author,
                        thumbnail=book.thumbnail,
                        publisher=book.publisher,
                        publisher_date=book.publisher_date,
                        language=book.language,
                        page_count=book.page_count,
                        categories=book.categories,
                    ),
                )
            )
        scored.sort(key=lambda pair: (-pair[0], pair[1].title.lower()))
        return [r for _, r in scored[:limit]]

    async def search_posts(
        self, *, query: str, viewer: "User | None", limit: int
    ) -> list[PostSearchResult]:
        qn = _normalize(query)
        if not qn:
            return []
        pool = self._pool_size(limit)
        candidates = await self.repo.search_posts(
            raw=query, normalized=qn, pool=pool
        )
        if not candidates:
            return []

        viewer_id = viewer.id if viewer is not None else None
        author_ids = {post.author_id for post, _, _ in candidates}
        profiles = await self.repo.get_profiles(author_ids)
        followed: set = set()
        blocked: set = set()
        muted: set = set()
        if viewer_id is not None:
            followed = await self.repo.followed_ids(viewer_id, author_ids)
            blocked = await self.repo.blocked_ids(viewer_id, author_ids)
            muted = await self.repo.muted_ids(viewer_id, author_ids)

        results: list[tuple[int, PostSearchResult]] = []
        for post, author, _ in candidates:
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
            result = PostSearchResult(
                id=str(post.id),
                type=post.type,
                body=post.body,
                visibility=post.visibility,
                book_id=post.book_id,
                created_at=post.created_at,
                author=UserSearchResult(
                    id=str(author.id),
                    username=author.username,
                    display_name=profile.display_name if profile else None,
                    avatar_url=profile.avatar_url if profile else None,
                ),
            )
            score = _score([qn], [_normalize(post.body)])
            results.append((score, result))

        results.sort(
            key=lambda pair: (-pair[0], pair[1].created_at.timestamp())
        )
        return [r for _, r in results[:limit]]

    @staticmethod
    def _pool_size(limit: int) -> int:
        return min(max(limit * 4, 20), 500)
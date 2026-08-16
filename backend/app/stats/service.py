"""Lógica de negocio del módulo stats (FASE 9).

Computa estadísticas de lectura derivadas (sin tablas propias):
libros leídos por año, páginas, avg rating, mejor género, racha de
lectura, total histórico y progreso del goal anual.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from app.core.visibility import is_visible
from app.stats.exceptions import StatsPrivateError, UserStatsNotFoundError
from app.stats.repository import StatsRepository
from app.stats.schemas import ReadingGoalProgress, ReadingStatsResponse

if TYPE_CHECKING:
    from app.auth.models import User


def _top_genre(books: list) -> str | None:
    """Género más frecuente (primera categoría de `categories`)."""
    counts: dict[str, int] = {}
    for _, book in books:
        categories = (book.categories or "").strip()
        if not categories:
            continue
        genre = categories.split(",")[0].strip()
        if genre:
            counts[genre] = counts.get(genre, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _streak(finished: list[date]) -> int:
    """Días consecutivos hacia atrás desde la última lectura terminada."""
    uniq = sorted({d for d in finished}, reverse=True)
    if not uniq:
        return 0
    streak = 1
    for prev, cur in zip(uniq, uniq[1:]):
        if (prev - cur).days == 1:
            streak += 1
        else:
            break
    return streak


def _pct(done: int, goal: int | None) -> float | None:
    if not goal:
        return None
    return round(min(done / goal, 2.0) * 100, 2)


class StatsService:
    def __init__(self, repository: StatsRepository) -> None:
        self.repo = repository

    async def get_stats(
        self,
        *,
        handle: str,
        viewer: "User | None",
        year: int,
    ) -> ReadingStatsResponse:
        target = await self.repo.get_user_by_handle(handle)
        if target is None:
            raise UserStatsNotFoundError()

        await self._check_visibility(target, viewer)

        rows = await self.repo.read_books_in_year(target.id, year)
        book_ids = [book.id for _, book in rows]
        ratings = await self.repo.get_ratings(target.id, book_ids)

        books_read = len(rows)
        pages_read = sum(book.page_count or 0 for _, book in rows)
        avg_rating = (
            round(sum(ratings.values()) / len(ratings), 2) if ratings else None
        )
        finished_dates = await self.repo.finished_dates(target.id)
        books_total = await self.repo.count_books(target.id)

        goal = await self.repo.get_goal(target.id, year)
        goal_progress = None
        if goal is not None:
            goal_progress = ReadingGoalProgress(
                books_read=books_read,
                books_goal=goal.books_goal,
                books_progress_pct=_pct(books_read, goal.books_goal),
                pages_read=pages_read,
                pages_goal=goal.pages_goal,
                pages_progress_pct=_pct(pages_read, goal.pages_goal),
            )

        return ReadingStatsResponse(
            user_id=str(target.id),
            year=year,
            books_read=books_read,
            pages_read=pages_read,
            avg_rating=avg_rating,
            top_genre=_top_genre(rows),
            streak_days=_streak(finished_dates),
            books_total=books_total,
            goal=goal_progress,
        )

    async def _check_visibility(self, target: "User", viewer: "User | None") -> None:
        viewer_id = viewer.id if viewer is not None else None
        if viewer_id is not None and viewer_id == target.id:
            return

        privacy = await self.repo.get_privacy(target.id)
        library_visibility = privacy.library_visibility if privacy else None

        if viewer_id is None and privacy is not None and privacy.block_anonymous:
            raise StatsPrivateError()

        is_follower = False
        is_blocked = False
        if viewer_id is not None:
            is_follower = (
                await self.repo.get_follow(viewer_id, target.id)
            ) is not None
            is_blocked = (
                await self.repo.get_block_relation(viewer_id, target.id)
            ) is not None

        if is_visible(
            section=library_visibility,
            viewer_id=viewer_id,
            author_id=target.id,
            is_follower=is_follower,
            is_blocked=is_blocked,
            author_active=True,
        ):
            return
        raise StatsPrivateError()
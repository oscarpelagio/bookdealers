"""Esquemas de validación del módulo stats."""

from __future__ import annotations

from datetime import date

from pydantic import Field
from sqlmodel import SQLModel


class ReadingGoalProgress(SQLModel):
    """Progreso del objetivo anual de lectura del usuario."""

    books_read: int = 0
    books_goal: int | None = None
    books_progress_pct: float | None = None
    pages_read: int = 0
    pages_goal: int | None = None
    pages_progress_pct: float | None = None


class ReadingStatsResponse(SQLModel):
    """Estadísticas de lectura de un usuario para un año."""

    user_id: str
    year: int
    books_read: int = 0
    pages_read: int = 0
    avg_rating: float | None = None
    top_genre: str | None = None
    streak_days: int = 0
    books_total: int = 0
    goal: ReadingGoalProgress | None = None
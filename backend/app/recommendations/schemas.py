"""Esquemas de validación del módulo de recomendaciones (FASE 11)."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import SQLModel

from app.enums import Visibility
from app.search.schemas import BookSearchResult
from app.social.schemas import UserBrief


class RecommendationItem(SQLModel):
    """Libro recomendado con el motivo de la recomendación."""

    book: BookSearchResult
    source: str  # popular | author | collaborative
    score: float = 0.0


class PopularPost(SQLModel):
    """Post popular del feed con su engagement."""

    id: str
    body: str
    visibility: Visibility
    like_count: int = 0
    comment_count: int = 0
    created_at: datetime
    author: UserBrief
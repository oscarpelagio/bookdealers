"""Dependencias de DI del módulo reviews.

Al importarse este módulo (vía el router) se registran los handlers de
eventos que mantienen los contadores de `books` (ADR-9).
"""

from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_db
from app.reviews.counters import register
from app.reviews.repository import ReviewRepository
from app.reviews.service import ReviewService

register()


def get_review_repository(db: AsyncSession = Depends(get_db)) -> ReviewRepository:
    return ReviewRepository(db)


def get_review_service(
    repo: ReviewRepository = Depends(get_review_repository),
    db: AsyncSession = Depends(get_db),
) -> ReviewService:
    return ReviewService(repo, db)

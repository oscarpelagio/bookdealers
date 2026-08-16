"""Dependencias del módulo de recomendaciones (FASE 11)."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.deps import get_db
from app.profiles.dependencies import get_optional_current_user
from app.recommendations.repository import RecommendationRepository
from app.recommendations.service import RecommendationService


async def get_recommendations_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[RecommendationService, None]:
    yield RecommendationService(RecommendationRepository(db))


def get_recommendations_deps(
    service: RecommendationService = Depends(get_recommendations_service),
    viewer: User | None = Depends(get_optional_current_user),
) -> dict:
    return {"service": service, "viewer": viewer}
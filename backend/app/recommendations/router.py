"""Rutas del módulo de recomendaciones (FASE 11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.recommendations.dependencies import get_recommendations_deps
from app.recommendations.schemas import PopularPost, RecommendationItem
from app.recommendations.service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
popular_router = APIRouter(prefix="/feed", tags=["recommendations"])


@router.get("", response_model=list[RecommendationItem])
async def get_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    deps: dict = Depends(get_recommendations_deps),
) -> list[RecommendationItem]:
    service: RecommendationService = deps["service"]
    return await service.get_recommendations(viewer=deps["viewer"], limit=limit)


@popular_router.get("/popular", response_model=list[PopularPost])
async def get_popular_posts(
    limit: int = Query(default=10, ge=1, le=50),
    deps: dict = Depends(get_recommendations_deps),
) -> list[PopularPost]:
    service: RecommendationService = deps["service"]
    return await service.get_popular_posts(viewer=deps["viewer"], limit=limit)
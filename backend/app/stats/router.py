"""Rutas del módulo stats (FASE 9)."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.stats.dependencies import get_stats_deps
from app.stats.schemas import ReadingStatsResponse
from app.stats.service import StatsService

router = APIRouter(prefix="/users", tags=["stats"])


@router.get("/{handle}/stats", response_model=ReadingStatsResponse)
async def get_user_stats(
    handle: str,
    year: int = Query(
        default=datetime.date.today().year,
        ge=2000,
        le=2100,
        description="Año del que se calculan las estadísticas.",
    ),
    deps: dict = Depends(get_stats_deps),
) -> ReadingStatsResponse:
    service: StatsService = deps["service"]
    viewer = deps["viewer"]
    return await service.get_stats(handle=handle, viewer=viewer, year=year)
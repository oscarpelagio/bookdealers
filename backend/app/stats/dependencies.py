"""Dependencias del módulo stats (FASE 9)."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.deps import get_db
from app.profiles.dependencies import get_optional_current_user
from app.stats.repository import StatsRepository
from app.stats.service import StatsService


async def get_stats_service(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[StatsService, None]:
    yield StatsService(StatsRepository(db))


def get_stats_deps(
    service: StatsService = Depends(get_stats_service),
    viewer: User | None = Depends(get_optional_current_user),
) -> dict:
    return {"service": service, "viewer": viewer}
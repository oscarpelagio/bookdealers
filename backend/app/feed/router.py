"""Endpoints del feed (routers finos, sin lógica)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.feed.dependencies import get_feed_service
from app.feed.service import FeedService
from app.social.schemas import ActivityPage

router = APIRouter()


@router.get(
    "/feed",
    response_model=ActivityPage,
    summary="Mi timeline: actividad de seguidos + propia (paginado por cursor)",
)
async def get_feed(
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    service: FeedService = Depends(get_feed_service),
) -> ActivityPage:
    return await service.get_feed(user, cursor=cursor, limit=limit)
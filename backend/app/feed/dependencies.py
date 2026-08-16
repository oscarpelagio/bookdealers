"""Dependencias de DI del módulo feed."""

from __future__ import annotations

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.deps import get_db
from app.feed.repository import FeedRepository
from app.feed.service import FeedService


def get_feed_repository(db: AsyncSession = Depends(get_db)) -> FeedRepository:
    return FeedRepository(db)


def get_feed_service(
    repo: FeedRepository = Depends(get_feed_repository),
    db: AsyncSession = Depends(get_db),
) -> FeedService:
    return FeedService(repo, db)
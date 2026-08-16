"""Dependències compartides de baix nivell (eviten imports circulars)."""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_session


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Obre una sessió per petició i la tanca automàticament."""
    async with async_session() as session:
        yield session


def get_db_dependency() -> type:
    """Retorna la dependència de base de dades per a overrides en tests."""
    return Depends(get_db)

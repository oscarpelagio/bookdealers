"""Repositori de l'índex d'autors de Libros del Asteroide."""

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters import AsteroideIndexEntry
from app.models import AsteroideAuthorIndex
from app.utils import NormalizationUtils


class AsteroideIndexRepository:
    """Operacions CRUD sobre `asteroide_author_index` (PK: slug)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def by_slug(self, slug: str) -> AsteroideAuthorIndex | None:
        result = await self.db.exec(
            select(AsteroideAuthorIndex).where(
                AsteroideAuthorIndex.slug == slug
            )
        )
        return result.first()

    async def by_normalized(self, name_normalized: str) -> list[AsteroideAuthorIndex]:
        result = await self.db.exec(
            select(AsteroideAuthorIndex).where(
                AsteroideAuthorIndex.name_normalized == name_normalized
            )
        )
        return list(result)

    async def all_view(self) -> list[tuple[str, str]]:
        """Parelles (name_normalized, slug) per matchejar en memòria."""
        result = await self.db.exec(
            select(AsteroideAuthorIndex.name_normalized, AsteroideAuthorIndex.slug)
        )
        return list(result)

    async def count(self) -> int:
        result = await self.db.exec(
            select(AsteroideAuthorIndex.slug)
        )
        return len(list(result))

    async def upsert_many(self, entries: list[AsteroideIndexEntry]) -> int:
        """Inserta entrades de l'índex (ON CONFLICT DO NOTHING)."""
        if not entries:
            return 0
        rows = [
            {
                "slug": e.slug,
                "name": e.name,
                "name_normalized": NormalizationUtils.normalize_text(e.name),
                "fetched_at": _now(),
            }
            for e in entries
        ]
        stmt = insert(AsteroideAuthorIndex).values(rows).on_conflict_do_nothing()
        result = await self.db.execute(stmt)
        await self.db.commit()
        return max(result.rowcount or 0, 0)


def _now():
    from datetime import datetime

    return datetime.utcnow()
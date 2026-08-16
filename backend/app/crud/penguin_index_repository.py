"""Repositori de l'índex d'autors de Penguin (`penguin_author_index`)."""

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters import PenguinIndexEntry
from app.models import PenguinAuthorIndex
from app.utils import NormalizationUtils


class PenguinIndexRepository:
    """Operacions CRUD sobre l'índex d'autors de Penguin."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, author_id: int) -> PenguinAuthorIndex | None:
        result = await self.db.exec(
            select(PenguinAuthorIndex).where(
                PenguinAuthorIndex.author_id == author_id
            )
        )
        return result.first()

    async def by_slug(self, slug: str) -> list[PenguinAuthorIndex]:
        result = await self.db.exec(
            select(PenguinAuthorIndex).where(PenguinAuthorIndex.slug == slug)
        )
        return list(result)

    async def by_normalized(self, name_normalized: str) -> list[PenguinAuthorIndex]:
        result = await self.db.exec(
            select(PenguinAuthorIndex).where(
                PenguinAuthorIndex.name_normalized == name_normalized
            )
        )
        return list(result)

    async def all_view(self) -> list[tuple[str, int]]:
        """Parelles (name_normalized, author_id) per matchejar en memòria."""
        result = await self.db.exec(
            select(PenguinAuthorIndex.name_normalized, PenguinAuthorIndex.author_id)
        )
        return list(result)

    async def ids(self) -> set[int]:
        result = await self.db.exec(select(PenguinAuthorIndex.author_id))
        return {row for row in result}

    async def upsert_many(
        self, entries: list[PenguinIndexEntry], seen_ids: set[int] | None = None
    ) -> int:
        """Inserta entrades de l'índex (ON CONFLICT DO NOTHING): segur per
        a workers concurrents, no llança per PK duplicada."""
        if not entries:
            return 0
        seen = seen_ids if seen_ids is not None else set()
        rows = [
            {
                "author_id": e.author_id,
                "name": e.name,
                "name_normalized": NormalizationUtils.normalize_text(e.name),
                "slug": e.slug,
                "thumb": e.thumb,
                "fetched_at": _now(),
            }
            for e in entries
        ]
        stmt = insert(PenguinAuthorIndex).values(rows).on_conflict_do_nothing()
        result = await self.db.execute(stmt)
        await self.db.commit()
        added = max(result.rowcount or 0, 0)
        seen.update(e.author_id for e in entries)
        return added


def _now():
    from datetime import datetime

    return datetime.utcnow()
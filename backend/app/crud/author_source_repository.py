"""Repositori unificat de fonts editorials d'autors (`author_source`)."""

from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import AuthorSource


class AuthorSourceRepository:
    """Operacions CRUD sobre `author_source` (PK: author_key + editorial)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, author_key: str, editorial: str) -> AuthorSource | None:
        result = await self.db.exec(
            select(AuthorSource).where(
                AuthorSource.author_key == author_key,
                AuthorSource.editorial == editorial,
            )
        )
        return result.first()

    async def sources_for(self, author_key: str) -> list[AuthorSource]:
        """Todos los registros (todas las editoriales) de un autor."""
        result = await self.db.exec(
            select(AuthorSource).where(AuthorSource.author_key == author_key)
        )
        return list(result)

    async def all(self) -> list[AuthorSource]:
        result = await self.db.exec(select(AuthorSource))
        return list(result)

    async def slugs_for_editorial(self, editorial: str) -> set[str]:
        """Slugs ja volcats d'una editorial (per reanudar volcats)."""
        result = await self.db.exec(
            select(AuthorSource.slug).where(
                AuthorSource.editorial == editorial,
                AuthorSource.slug.is_not(None),
            )
        )
        return {slug for slug in result if slug}

    async def upsert(
        self,
        author_key: str,
        editorial: str,
        name: str,
        slug: str | None,
        description: str | None,
        image_url: str | None,
    ) -> AuthorSource:
        source = await self.get(author_key, editorial)
        now = datetime.utcnow()
        if source is not None:
            source.name = name
            source.slug = slug
            source.description = description
            source.image_url = image_url
            source.fetched_at = now
        else:
            source = AuthorSource(
                author_key=author_key,
                editorial=editorial,
                name=name,
                slug=slug,
                description=description,
                image_url=image_url,
                fetched_at=now,
            )
            self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Upsert massiu (ON CONFLICT DO UPDATE) per al seed d'arrencada."""
        if not rows:
            return 0
        stmt = insert(AuthorSource).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="author_source_pkey",
            set_={
                "name": stmt.excluded.name,
                "slug": stmt.excluded.slug,
                "description": stmt.excluded.description,
                "image_url": stmt.excluded.image_url,
                "fetched_at": stmt.excluded.fetched_at,
            },
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return max(result.rowcount or 0, 0)

"""Repositori unificat de fonts editorials d'autors (`author_source`)."""

from datetime import datetime

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

    async def upsert(
        self,
        author_key: str,
        editorial: str,
        name: str,
        slug: str | None,
        description: str | None,
        image_url: str | None,
        extra: list | None,
    ) -> AuthorSource:
        source = await self.get(author_key, editorial)
        now = datetime.utcnow()
        if source is not None:
            source.name = name
            source.slug = slug
            source.description = description
            source.image_url = image_url
            source.extra = extra or None
            source.fetched_at = now
        else:
            source = AuthorSource(
                author_key=author_key,
                editorial=editorial,
                name=name,
                slug=slug,
                description=description,
                image_url=image_url,
                extra=extra or None,
                fetched_at=now,
            )
            self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        return source
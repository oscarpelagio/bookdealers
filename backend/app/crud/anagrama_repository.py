"""Repositori per al volcat d'autors d'Anagrama."""

from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import AuthorAnagrama


class AnagramaRepository:
    """Operacions CRUD sobre `authors_anagrama` (upsert per slug)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, slug: str) -> AuthorAnagrama | None:
        result = await self.db.exec(
            select(AuthorAnagrama).where(AuthorAnagrama.slug == slug)
        )
        return result.first()

    async def all(self) -> list[AuthorAnagrama]:
        result = await self.db.exec(select(AuthorAnagrama))
        return list(result)

    async def fetched_slugs(self) -> set[str]:
        result = await self.db.exec(select(AuthorAnagrama.slug))
        return {row for row in result}

    async def upsert(
        self,
        slug: str,
        name: str,
        description: str | None,
        image_url: str | None,
        extra: list | None,
    ) -> AuthorAnagrama:
        author = await self.get(slug)
        now = datetime.utcnow()
        if author is not None:
            author.name = name
            author.description = description
            author.image_url = image_url
            author.extra = extra
            author.fetched_at = now
        else:
            author = AuthorAnagrama(
                slug=slug,
                name=name,
                description=description,
                image_url=image_url,
                extra=extra,
                fetched_at=now,
            )
            self.db.add(author)
        await self.db.commit()
        await self.db.refresh(author)
        return author

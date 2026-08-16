"""Repositori per al volcat d'autors de Blackie Books."""

from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import AuthorBlackie


class BlackieRepository:
    """Operacions CRUD sobre `authors_blackie` (upsert per slug)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, slug: str) -> AuthorBlackie | None:
        result = await self.db.exec(
            select(AuthorBlackie).where(AuthorBlackie.slug == slug)
        )
        return result.first()

    async def all(self) -> list[AuthorBlackie]:
        result = await self.db.exec(select(AuthorBlackie))
        return list(result)

    async def fetched_slugs(self) -> set[str]:
        result = await self.db.exec(select(AuthorBlackie.slug))
        return {row for row in result}

    async def upsert(
        self,
        slug: str,
        name: str,
        description: str | None,
        image_url: str | None,
    ) -> AuthorBlackie:
        author = await self.get(slug)
        now = datetime.utcnow()
        if author is not None:
            author.name = name
            author.description = description
            author.image_url = image_url
            author.fetched_at = now
        else:
            author = AuthorBlackie(
                slug=slug,
                name=name,
                description=description,
                image_url=image_url,
                fetched_at=now,
            )
            self.db.add(author)
        await self.db.commit()
        await self.db.refresh(author)
        return author
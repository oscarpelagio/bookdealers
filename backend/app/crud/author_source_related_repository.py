"""Repositori d'articles relacionats d'un autor editorial (`author_source_related`)."""

from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import AuthorSourceRelated


class AuthorSourceRelatedRepository:
    """Operacions CRUD sobre `author_source_related` (1:molts de author_source)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def for_source(self, author_key: str, editorial: str) -> list[AuthorSourceRelated]:
        """Ítems d'un perfil, en ordre original."""
        result = await self.db.exec(
            select(AuthorSourceRelated)
            .where(
                AuthorSourceRelated.author_key == author_key,
                AuthorSourceRelated.editorial == editorial,
            )
            .order_by(AuthorSourceRelated.posicion)
        )
        return list(result)

    async def replace(
        self, author_key: str, editorial: str, items: list[dict] | None
    ) -> None:
        """Substitueix tots els ítems d'un perfil per `items` (idempotent)."""
        await self.db.exec(
            delete(AuthorSourceRelated).where(
                AuthorSourceRelated.author_key == author_key,
                AuthorSourceRelated.editorial == editorial,
            )
        )
        for posicion, item in enumerate(items or []):
            self.db.add(
                AuthorSourceRelated(
                    author_key=author_key,
                    editorial=editorial,
                    posicion=posicion,
                    tipo=item.get("tipo"),
                    titulo=item.get("titulo"),
                    url=item.get("url"),
                    fecha=item.get("fecha"),
                    descripcion=item.get("descripcion"),
                    thumbnail=item.get("thumbnail"),
                    categoria=item.get("categoria"),
                )
            )
        await self.db.commit()

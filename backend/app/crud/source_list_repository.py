"""Repositori de les llistes genèriques de fonts web (sourced_lists)."""

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import SourceList, SourceListBook

DEFAULT_SOURCE = "lacentral"


class SourceListRepository:
    """Operacions CRUD sobre `sourced_lists` i `sourced_list_books`."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_slug(self, slug: str, source: str = DEFAULT_SOURCE) -> SourceList | None:
        """Cerca una llista pel seu slug dins d'una font."""
        result = await self.db.exec(
            select(SourceList).where(
                SourceList.slug == slug,
                SourceList.source == source,
            )
        )
        return result.first()

    async def books_in_list(self, list_id: int) -> list[SourceListBook]:
        """Entrades (llibres) d'una llista ordenades per posició."""
        result = await self.db.exec(
            select(SourceListBook)
            .where(SourceListBook.list_id == list_id)
            .order_by(SourceListBook.posicion)
        )
        return list(result)

    async def set_book_id(self, entry_id: int, book_id: int) -> None:
        """Guarda el llibre del catàleg resolt per a una entrada."""
        entry = await self.db.get(SourceListBook, entry_id)
        if entry is not None:
            entry.book_id = book_id
            await self.db.commit()

    async def book_appears_in(
        self, normal_title: str, normal_author: str
    ) -> list[tuple[SourceList, int]]:
        """Llistes on apareix un llibre (per títol + autor normalitzats).

        Retorna una llista de (llista, posicio del llibre) ordenada per data
        descendent (més recents primer).
        """
        if not normal_title or not normal_author:
            return []
        stmt = (
            select(SourceList, SourceListBook.posicion)
            .join(
                SourceListBook,
                SourceListBook.list_id == SourceList.id,
            )
            .where(
                SourceListBook.titulo_normalizado == normal_title,
                SourceListBook.autor_normalizado == normal_author,
            )
            .order_by(SourceList.fecha.desc().nullslast(), SourceList.id.desc())
        )
        result = await self.db.exec(stmt)
        return list(result)

    async def lists_by_author(
        self, normal_author: str
    ) -> list[tuple[SourceList, int]]:
        """Llistes on apareix ALGUN llibre d'un autor (per autor normalitzat).

        Retorna (llista, posicio del primer llibre trobat de l'autor) ordenat
        per data descendent. Una mateixa llista només surt una vegada.
        """
        if not normal_author:
            return []
        rows = (
            await self.db.exec(
                select(
                    SourceList,
                    SourceListBook.posicion,
                )
                .join(
                    SourceListBook,
                    SourceListBook.list_id == SourceList.id,
                )
                .where(SourceListBook.autor_normalizado == normal_author)
                .order_by(
                    SourceList.fecha.desc().nullslast(),
                    SourceList.id.desc(),
                )
            )
        ).all()
        lists: dict[int, tuple[SourceList, int]] = {}
        for slist, posicion in rows:
            if slist.id not in lists:
                lists[slist.id] = (slist, posicion)
        return list(lists.values())

    async def bulk_upsert(self, rows: list[dict]) -> int:
        """Insereix llistes (ON CONFLICT DO NOTHING per (source, slug))."""
        if not rows:
            return 0
        stmt = (
            insert(SourceList)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["source", "slug"])
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return max(result.rowcount or 0, 0)

    async def create_from_seed(self, slist: SourceList, books: list[dict]) -> SourceList:
        """Crea una llista amb els seus llibres (materialització perezosa)."""
        self.db.add(slist)
        await self.db.flush()
        book_rows = [{**b, "list_id": slist.id} for b in books]
        await self.replace_books(slist.id, book_rows)
        await self.db.refresh(slist)
        return slist

    async def replace_books(self, list_id: int, book_rows: list[dict]) -> None:
        """Esborra els llibres d'una llista i insereix els nous."""
        old = await self.db.exec(
            select(SourceListBook).where(SourceListBook.list_id == list_id)
        )
        for book in old:
            await self.db.delete(book)
        if book_rows:
            self.db.add_all(SourceListBook(**row) for row in book_rows)
        await self.db.commit()

    async def count(self) -> tuple[int, int]:
        """(llistes totals, llistes fetes)."""
        total = len((await self.db.exec(select(SourceList))).all())
        done = len(
            (
                await self.db.exec(
                    select(SourceList).where(SourceList.status == "done")
                )
            ).all()
        )
        return total, done
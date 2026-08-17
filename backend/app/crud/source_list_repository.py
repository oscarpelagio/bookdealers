"""Repositori de les llistes genèriques de fonts web (sourced_lists)."""

from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Book, SourceList, SourceListBook

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

    async def bulk_upsert_books(
        self, source: str, slug: str, book_rows: list[dict]
    ) -> int:
        """Insereix els llibres d'una llista si encara no existeixen.

        Idempotent per (list_id, posicion): no esborra res, així que les
        entrades ja resoltes (amb `book_id`) es conserven entre reinicis.
        Retorna quants llibres s'han inserit.
        """
        target = await self.get_by_slug(slug, source)
        if target is None or not book_rows:
            return 0
        existing = await self.db.exec(
            select(SourceListBook.posicion).where(SourceListBook.list_id == target.id)
        )
        have = {pos for (pos,) in existing.all()}

        # book_id del seed resolt contra una altra BD (o obsolet) no existeix
        # aquí: es posa a NULL i es resol per Z39.50 a la consulta.
        wanted_ids = [row.get("book_id") for row in book_rows if row.get("book_id")]
        if wanted_ids:
            found = (
                await self.db.exec(select(Book.id).where(Book.id.in_(wanted_ids)))
            ).all()
            valid_ids = {fid for (fid,) in found}
        else:
            valid_ids = set()

        to_insert = []
        for row in book_rows:
            if row["posicion"] in have:
                continue
            entry = {**row, "list_id": target.id}
            if entry.get("book_id") not in valid_ids:
                entry["book_id"] = None
            to_insert.append(entry)
        if to_insert:
            self.db.add_all(SourceListBook(**row) for row in to_insert)
            await self.db.commit()
        return len(to_insert)

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
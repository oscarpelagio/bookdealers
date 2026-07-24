"""Repositori per a operacions CRUD de disponibilitat."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.schemas import AvailabilityBase
from app.models import BookEstablishment, Establishment, Book, Catalog


class AvailabilityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_availability(self, book: Book, catalog: Catalog):
        """
        Retorna la disponibilitat guardada d'un llibre, o None si no en té.
        """
        statement = (
            select(BookEstablishment)
            .join(Establishment, BookEstablishment.establishment_id == Establishment.id)
            .where(BookEstablishment.book_id == book.id)
            .where(Establishment.catalog_id == catalog.id)
        )
        result = await self.db.exec(statement)
        return result.all()

    async def save_availability(self, availability: list[AvailabilityBase]): 
        """
        Guarda la disponibilitat d'un llibre a les biblioteques.
        Espera una llista de dicts amb claus: biblioteca, language, estado.
        """
        for item in availability:
            statement = select(Establishment).where(Establishment.name == item.establishment_name)
            result = await self.db.exec(statement)
            establishment = result.first()

            if not establishment:
                establishment = Establishment(name=item.establishment_name, 
                                              type=item.establishment_type,
                                              catalog_id=item.catalog_id)                
                self.db.add(establishment)
                await self.db.commit()
                await self.db.refresh(establishment)

            # Comprovar si ja existeix la relació
            statement = select(BookEstablishment).where(
                BookEstablishment.book_id == item.book_id,
                BookEstablishment.establishment_id == establishment.id,
                BookEstablishment.language == item.book_language,
            )
            result = await self.db.exec(statement)
            existing = result.first()

            if existing:
                existing.status = item.book_status
            else:
                be = BookEstablishment(
                    book_id=item.book_id,
                    establishment_id=establishment.id,
                    language=item.book_language,
                    status=item.book_status,
                    queue=item.queue,
                    link=item.link
                )
                self.db.add(be)

        await self.db.commit()

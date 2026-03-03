"""Repositori per a operacions CRUD de disponibilitat."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import BookEstablishment, Establishment


class AvailabilityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_availability(self, book_id: int) -> list[dict] | None:
        """
        Retorna la disponibilitat guardada d'un llibre, o None si no en té.
        """
        statement = (
            select(BookEstablishment, Establishment)
            .join(Establishment, BookEstablishment.establishment_id == Establishment.id)
            .where(BookEstablishment.book_id == book_id)
        )
        result = await self.db.exec(statement)
        rows = result.all()
        if not rows:
            return None
        return [
            {
                "biblioteca": establishment.name,
                "language": be.language,
                "estado": be.status,
            }
            for be, establishment in rows
        ]

    async def save_availability(self, book_id: int, availability: list[dict]):
        """
        Guarda la disponibilitat d'un llibre a les biblioteques.
        Espera una llista de dicts amb claus: biblioteca, language, estado.
        """
        for item in availability:
            # Buscar o crear l'establiment
            statement = select(Establishment).where(Establishment.name == item["biblioteca"])
            result = await self.db.exec(statement)
            establishment = result.first()

            if not establishment:
                establishment = Establishment(name=item["biblioteca"], type="library")
                self.db.add(establishment)
                await self.db.commit()
                await self.db.refresh(establishment)

            # Comprovar si ja existeix la relació
            statement = select(BookEstablishment).where(
                BookEstablishment.book_id == book_id,
                BookEstablishment.establishment_id == establishment.id,
                BookEstablishment.language == item["language"],
            )
            result = await self.db.exec(statement)
            existing = result.first()

            if existing:
                existing.status = item["estado"]
            else:
                be = BookEstablishment(
                    book_id=book_id,
                    establishment_id=establishment.id,
                    language=item["language"],
                    status=item["estado"],
                )
                self.db.add(be)

        await self.db.commit()

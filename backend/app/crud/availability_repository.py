"""Repositori per a operacions CRUD de disponibilitat."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import timedelta, datetime
from sqlalchemy import or_
from app.schemas import AvailabilityBase
from app.models import BookEstablishment, Establishment, Book, Catalog, SeedAladi
from app.core.seed_aladi import (
    link_library_to_seed,
    _street_seed,
)


class AvailabilityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_availability(self, book: Book, catalog: Catalog):
        """
        Retorna la disponibilitat guardada d'un llibre, o None si no en té.

        Per a biblioteques del catàleg aladi, si la fila seed_aladi està
        enllaçada (id_establishment), es mostren el nom, municipi i carrer
        ben formats del volcat DIBA en lloc de les dades pròpies.
        """
        statement = (
            select(BookEstablishment, Establishment, SeedAladi)
            .join(Establishment, BookEstablishment.establishment_id == Establishment.id)
            .outerjoin(SeedAladi, SeedAladi.id_establishment == Establishment.id)
            .where(BookEstablishment.updated_at > datetime.utcnow() - timedelta(hours=24))
            .where(BookEstablishment.book_id == book.id)
            .where(Establishment.catalog_id == catalog.id)
        )
        result = await self.db.exec(statement)
        rows = result.all()
        return [
            self._build_entry(be, est, seed)
            for be, est, seed in rows
        ]

    @staticmethod
    def _build_entry(be, est, seed):
        """Construeix una entrada de disponibilitat; si hi ha match aladi es
        prioritzen els camps del volcat (nom, municipi, carrer)."""
        if seed is not None:
            establishment_name = seed.nom or est.name
            establishment_city = seed.municipi or est.city
            establishment_street = _street_seed(seed.adreca, seed.codi_postal, seed.municipi) or est.street
            establishment_postal_code = seed.codi_postal or est.postal_code
        else:
            establishment_name = est.name
            establishment_city = est.city
            establishment_street = est.street
            establishment_postal_code = est.postal_code

        return {
            "establishment_type": est.type,
            "establishment_name": establishment_name,
            "establishment_street": establishment_street,
            "establishment_postal_code": establishment_postal_code,
            "establishment_city": establishment_city,
            "establishment_province": est.province,
            "lat": seed.lat if seed is not None else None,
            "lon": seed.lon if seed is not None else None,
            "catalog_id": est.catalog_id,
            "book_id": be.book_id,
            "book_language": be.language,
            "book_status": be.status.name if be.status is not None else None,
            "queue": be.queue,
            "link": be.link,
        }

    async def get_outdated_availability(
        self,
        days: int,
        service: str | None = None,
        catalog_name: str | None = None,
    ) -> list[tuple[int, str]]:
        """
        Retorna parells (book_id, catalog_name) amb disponibilitat caducada.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        statement = (
            select(BookEstablishment.book_id, Catalog.name)
            .join(Establishment, BookEstablishment.establishment_id == Establishment.id)
            .join(Catalog, Establishment.catalog_id == Catalog.id)
            .where(or_(BookEstablishment.updated_at == None, BookEstablishment.updated_at < cutoff))
        )
        if service:
            statement = statement.where(Catalog.service == service)
        if catalog_name:
            statement = statement.where(Catalog.name == catalog_name)

        result = await self.db.exec(statement.distinct())
        return result.all()

    async def save_availability(self, availability: list[AvailabilityBase]): 
        """
        Guarda la disponibilitat d'un llibre a les biblioteques.
        Espera una llista de dicts amb claus: biblioteca, language, estado.
        """
        now = datetime.utcnow()
        for item in availability:
            statement = select(Establishment).where(Establishment.name == item.establishment_name)
            result = await self.db.exec(statement)
            establishment = result.first()

            if not establishment:
                establishment = Establishment(
                    name=item.establishment_name,
                    type=item.establishment_type,
                    catalog_id=item.catalog_id,
                    street=item.establishment_street,
                    postal_code=item.establishment_postal_code,
                    city=item.establishment_city,
                    province=item.establishment_province,
                )
                self.db.add(establishment)
                await self.db.commit()
                await self.db.refresh(establishment)
                # Biblioteca nova: enllaça amb la fila seed_aladi més semblant.
                await link_library_to_seed(self.db, establishment)
            else:
                updated = False
                if item.establishment_street and not establishment.street:
                    establishment.street = item.establishment_street
                    updated = True
                if item.establishment_postal_code and not establishment.postal_code:
                    establishment.postal_code = item.establishment_postal_code
                    updated = True
                if item.establishment_city and not establishment.city:
                    establishment.city = item.establishment_city
                    updated = True
                if item.establishment_province and not establishment.province:
                    establishment.province = item.establishment_province
                    updated = True
                if updated:
                    establishment.updated_at = now

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
                existing.queue = item.queue
                existing.link = item.link
                existing.updated_at = now
            else:
                be = BookEstablishment(
                    book_id=item.book_id,
                    establishment_id=establishment.id,
                    language=item.book_language,
                    status=item.book_status,
                    queue=item.queue,
                    link=item.link,
                    updated_at=now,
                )
                self.db.add(be)

        await self.db.commit()

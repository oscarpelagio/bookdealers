"""
Servei per consultar disponibilitat a Todostuslibros.

Además de persistir la disponibilidad, captura el precio del libro que
todostuslibros publica en el HTML de búsqueda y lo guarda en `book.price`
(es un precio único por libro, independiente de la librería).
"""

from decimal import Decimal

from app.services import AvailabilityBaseService


class TodostuslibrosService(AvailabilityBaseService):
    SERVICE_NAME = "todostuslibros"

    async def get_availabity(self, book_id: int, catalog: str):
        result = await super().get_availabity(book_id, catalog)
        price: Decimal | None = getattr(self.client, "last_price", None)
        if price is not None:
            await self.book_repository.update_price(book_id, price)
        return result

"""
Servei per consultar disponibilitat al catàleg ALADI via Z39.50.
"""

from app.adapters import Z3950Adapter
from app.clients import Z3950Client
from app.crud import BookRepository, AvailabilityRepository

class Z3950Service:
    def __init__(
        self, 
        book_repo: BookRepository,
        availability_repo: AvailabilityRepository,
        client: Z3950Client,
        adapter: Z3950Adapter
        
    ):
        self.book_repository = book_repo
        self.availability_repository = availability_repo
        self.client = client
        self.adapter = adapter

    async def search_book(self, book_id: int):

        # Comprova si ja tenim la disponibilitat guardada
        cached = await self.availability_repository.get_availability(book_id)
        if cached:
            return cached

        book = await self.book_repository.get_by_id(book_id)
        title = book.normal_title
        author = book.normal_author
        respuesta = await self.client.search_z3950(title, author)
        localizaciones = self.adapter.extraer_localizaciones(respuesta)
        await self.availability_repository.save_availability(book_id, localizaciones)
        return localizaciones

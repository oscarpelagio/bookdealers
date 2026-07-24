"""Paquet de rutes de l'API."""

from .dependencies import (
	get_google_books_service,
	get_open_library_service,
	get_book_repository,
	get_google_client,
	get_db,
	get_z3950_service,
	get_ebiblio_service,
	get_todostuslibros_service,
)
from .router import api_router

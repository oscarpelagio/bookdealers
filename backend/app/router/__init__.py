"""Paquet de rutes de l'API."""

from .dependencies import (
	get_google_books_service,
	get_open_library_service,
	get_z3950_search_service,
	get_z3950_import_service,
	get_book_repository,
	get_google_client,
	get_db,
	get_z3950_service,
	get_ebiblio_service,
	get_todostuslibros_service,
	get_auth_repository,
	get_auth_service,
	get_current_user,
	get_google_verifier,
	require_roles,
	get_author_photo_service,
	get_author_source_related_repository,
	get_author_profile_lookup_service,
	get_central_article_repository,
)
from .router import api_router

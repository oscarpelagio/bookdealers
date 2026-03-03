"""Paquet de rutes de l'API."""

from .dependencies import get_book_service, get_book_repository, get_google_client, get_db, get_user, get_z3950_service
from .router import api_router
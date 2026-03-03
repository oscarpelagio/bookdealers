"""Paquet d'esquemes de validació per a l'API."""

from .book import BookBase, BookCreate, BookUpdate, BookResponse, BookSearchResponse

__all__ = ["BookBase", "BookCreate", "BookUpdate", "BookResponse", "BookSearchResponse"]

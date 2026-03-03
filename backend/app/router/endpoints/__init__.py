"""Paquet de gestors d'endpoints de l'API v1."""

from .search_router import router as search_router
from .import_router import router as import_router
from .z3950_router import router as z3950_router
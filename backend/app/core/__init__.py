"""Paquet de configuració central i base de dades."""

from .config import settings

__all__ = ["settings", "create_db_and_tables"]

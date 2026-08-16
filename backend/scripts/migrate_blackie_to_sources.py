"""Migració de `authors_blackie` a la taula unificada `author_source`.

Cada autor existent es guarda amb `editorial='blackie'` i `author_key`
normalitzat (format "Nombre Apellido", sense accents). Upsert: repetible,
no duplica ni borra res.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/migrate_blackie_to_sources.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.crud import AuthorSourceRepository, BlackieRepository
from app.core.db import async_session
from app.utils import NormalizationUtils

EDITORIAL = "blackie"


async def main() -> None:
    async with async_session() as db:
        authors = await BlackieRepository(db).all()
        repo = AuthorSourceRepository(db)
        ok = 0
        skipped = 0
        for author in authors:
            author_key = NormalizationUtils.normalize_text(
                NormalizationUtils.author_name_first(author.name)
            )
            if not author_key:
                skipped += 1
                continue
            await repo.upsert(
                author_key=author_key,
                editorial=EDITORIAL,
                name=author.name,
                slug=author.slug,
                description=author.description,
                image_url=author.image_url,
                extra=None,
            )
            ok += 1
        print(f"[migrate] {ok} autors de Blackie Books a `author_source` | skip: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
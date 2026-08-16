"""Precàrrega de l'índex d'autors de Libros del Asteroide.

Recull el llistat `/autores` (una sola pàgina, ~241 autors) i guarda
slug + nom a `asteroide_author_index`. No descarrega perfils: això ho fa el
lookup peresós (`/author-profile`) per autor concret.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/scrape_asteroide_index.py
    docker compose exec back python scripts/scrape_asteroide_index.py --refresh
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients import AsteroideClient
from app.core.db import async_session
from app.crud import AsteroideIndexRepository


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Precàrrega índex d'autors de Libros del Asteroide"
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-insereix tot (ON CONFLICT DO NOTHING no duplica)",
    )
    args = parser.parse_args()

    client = AsteroideClient()
    try:
        entries = await client.get_authors_index()
    finally:
        await client.aclose()

    async with async_session() as db:
        added = await AsteroideIndexRepository(db).upsert_many(entries)

    print(f"[asteroide-index] {len(entries)} autors al llistat | nous: {added}")


if __name__ == "__main__":
    asyncio.run(main())

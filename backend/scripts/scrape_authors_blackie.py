"""Volcat d'autors de l'editorial Blackie Books a la taula `authors_blackie`.

Cada autor es guarda amb: nom, bio (`description`) i enllaç directe a la
foto (`image_url`). Els slugs surten de l'índex `/autores/` (una sola
pàgina).

Agressiu per defecte (8 workers en paral·lel); si el servidor respon
429/403 el volcat avisa i ralentitza de forma adaptativa.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/scrape_authors_blackie.py
    docker compose exec back python scripts/scrape_authors_blackie.py --limit 5
    docker compose exec back python scripts/scrape_authors_blackie.py --workers 12
    docker compose exec back python scripts/scrape_authors_blackie.py --refresh
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients import BlackieClient
from app.core.db import async_session
from app.services import BlackieScraperService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Volcat d'autors de Blackie Books")
    parser.add_argument("--limit", type=int, default=None, help="Nombre màxim de perfils a processar")
    parser.add_argument("--workers", type=int, default=8, help="Workers en paral·lel (default 8)")
    parser.add_argument("--refresh", action="store_true", help="Re-descarrega tot (ignora fetched_at)")
    args = parser.parse_args()

    client = BlackieClient()
    try:
        service = BlackieScraperService(client, async_session, workers=args.workers)
        stats = await service.scrape(
            limit=args.limit,
            refresh=args.refresh,
        )
    finally:
        await client.aclose()

    print("\n=== RESUM VOLCAT BLACKIE ===")
    print(f"OK: {stats.ok} | fails: {stats.failed} | rate-limited: {stats.rate_limited}")
    print(f"amb foto: {stats.with_photo}")
    print(f"temps: {stats.elapsed:.1f}s")
    if stats.failures:
        print("fallades:")
        for slug, err in stats.failures[:20]:
            print(f"  - {slug}: {err}")


if __name__ == "__main__":
    asyncio.run(main())
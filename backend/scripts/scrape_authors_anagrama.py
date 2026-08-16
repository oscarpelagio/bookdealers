"""Volcat d'autors de l'editorial Anagrama a la taula `authors_anagrama`.

Cada autor es guarda amb: nom, bio (`description`), enllaç directe a la
foto (`image_url`) i el bloc de "contenido relacionado" (`extra`, tots els
tipus: videos/entrevistes/articles...).

Agressiu per defecte (8 workers en paral·lel); si el servidor respon
429/403 el volcat avisa i ralentitza de forma adaptativa.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/scrape_authors_anagrama.py
    docker compose exec back python scripts/scrape_authors_anagrama.py --limit 5
    docker compose exec back python scripts/scrape_authors_anagrama.py --workers 12
    docker compose exec back python scripts/scrape_authors_anagrama.py --letter m
    docker compose exec back python scripts/scrape_authors_anagrama.py --refresh
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients import AnagramaClient
from app.core.db import async_session
from app.services import AnagramaScraperService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Volcat d'autors d'Anagrama")
    parser.add_argument("--limit", type=int, default=None, help="Nombre màxim de perfils a processar")
    parser.add_argument("--workers", type=int, default=8, help="Workers en paral·lel (default 8)")
    parser.add_argument("--letter", type=str, default=None, help="Només una lletra de l'índex (per proves)")
    parser.add_argument("--refresh", action="store_true", help="Re-descarrega tot (ignora fetched_at)")
    args = parser.parse_args()

    client = AnagramaClient()
    try:
        service = AnagramaScraperService(client, async_session, workers=args.workers)
        stats = await service.scrape(
            limit=args.limit,
            refresh=args.refresh,
            letters=args.letter,
        )
    finally:
        await client.aclose()

    print("\n=== RESUM VOLCAT ANAGRAMA ===")
    print(f"OK: {stats.ok} | fails: {stats.failed} | rate-limited: {stats.rate_limited}")
    print(f"amb foto: {stats.with_photo} | amb extra (contingut relacionat): {stats.with_extra}")
    print(f"temps: {stats.elapsed:.1f}s")
    if stats.failures:
        print("fallades:")
        for slug, err in stats.failures[:20]:
            print(f"  - {slug}: {err}")


if __name__ == "__main__":
    asyncio.run(main())

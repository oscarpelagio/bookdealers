"""Precàrrega de l'índex d'autors de Penguin a `penguin_author_index`.

Recorre les pàgines del índex `/es/5-autores?pageno=N` (fins a ~1347 pàgines,
~16k autors) i guarda només nom + id + slug + miniatura. No descarrega
perfils: això ho fa el lookup peresós (`/author-profile`) per autor concret.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/scrape_penguin_index.py
    docker compose exec back python scripts/scrape_penguin_index.py --pages 20
    docker compose exec back python scripts/scrape_penguin_index.py --workers 12
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients import PenguinClient
from app.clients.anagrama_client import RateLimitedError
from app.core.db import async_session
from app.crud import PenguinIndexRepository

MAX_PAGES = 1347
MAX_RETRIES = 6
BASE_DELAY = 4.0


async def main() -> None:
    parser = argparse.ArgumentParser(description="Precàrrega índex d'autors de Penguin")
    parser.add_argument("--pages", type=int, default=MAX_PAGES, help="Pàgines a recórrer (default tot)")
    parser.add_argument("--workers", type=int, default=4, help="Workers en paral·lel (default 4)")
    args = parser.parse_args()

    client = PenguinClient(min_delay=BASE_DELAY)
    seen: set[int] = set()
    ok = failed = 0
    failures: list[tuple[int, str]] = []

    async def process(page: int) -> None:
        nonlocal ok, failed
        for attempt in range(MAX_RETRIES):
            try:
                entries = await client.get_index_page(page)
                async with async_session() as db:
                    await PenguinIndexRepository(db).upsert_many(entries, seen)
                ok += len(entries)
                return
            except RateLimitedError as exc:
                await asyncio.sleep(3 + attempt * 4)
                if attempt == MAX_RETRIES - 1:
                    failed += 1
                    failures.append((page, repr(exc)))
            except Exception as exc:
                await asyncio.sleep(1 + attempt * 2)
                if attempt == MAX_RETRIES - 1:
                    failed += 1
                    failures.append((page, repr(exc)))

    try:
        sem = asyncio.Semaphore(args.workers)

        async def guarded(page: int) -> None:
            async with sem:
                await process(page)

        for batch_start in range(0, args.pages, args.workers):
            await asyncio.gather(
                *(guarded(p) for p in range(batch_start + 1, min(batch_start + args.workers, args.pages) + 1))
            )
            if (batch_start // args.workers) % 25 == 0:
                print(f"[penguin-index] avanç pàgina {batch_start}/{args.pages} | ok={ok} fail={failed}", flush=True)
    finally:
        await client.aclose()

    print("\n=== RESUM ÍNDEX PENGUIN ===")
    print(f"entries ok: {ok} | pàgines fallades: {failed}")
    if failures:
        print("fallades (primeres 20):")
        for page, err in failures[:20]:
            print(f"  - pàgina {page}: {err}")


if __name__ == "__main__":
    asyncio.run(main())
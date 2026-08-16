"""Ompla `penguin_author_index` des del sitemap de categories de Penguin.

El sitemap `sitemap-categories-1-es-1.xml` inclou les pàgines de perfil de
tots els autors com a categories de PrestaShop (`/es/{id}-{slug}`), sense
rate-limit (a diferència de l'índex paginat AJAX). D'aquí s'extrauen
`author_id` + `slug` + nom derivat per al matcher per slug del lazy lookup.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/build_penguin_index_from_sitemap.py
"""

import argparse
import asyncio
import os
import re
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters import PenguinIndexEntry
from app.core.db import async_session
from app.crud import PenguinIndexRepository

SITEMAP_URL = "https://www.penguinlibros.com/es/sitemap-categories-1-es-1.xml"
_URL_RE = re.compile(r"<loc>([^<]+)</loc>")
_SLUG_RE = re.compile(r"/es/(\d+)-([a-z0-9-]+?)/?$")
BATCH_SIZE = 500


def _name_from_slug(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-") if part)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ompla l'índex d'autors Penguin des del sitemap")
    parser.add_argument("--clear", action="store_true", help="Buidar la taula abans d'omplir")
    args = parser.parse_args()

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=120.0,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    ) as client:
        response = await client.get(SITEMAP_URL)
        response.raise_for_status()
        urls = _URL_RE.findall(response.text)

    entries: list[PenguinIndexEntry] = []
    for url in urls:
        match = _SLUG_RE.search(url)
        if not match:
            continue
        author_id, slug = int(match.group(1)), match.group(2).strip("-")
        if not slug:
            continue
        entries.append(
            PenguinIndexEntry(
                author_id=author_id,
                slug=slug,
                name=_name_from_slug(slug),
                thumb=None,
            )
        )

    unique = {e.author_id: e for e in entries}
    entries = list(unique.values())
    print(f"[sitemap] {len(entries)} pàgines d'autor trobades")

    async with async_session() as db:
        repo = PenguinIndexRepository(db)
        if args.clear:
            from sqlalchemy import text

            await db.exec(text("TRUNCATE TABLE penguin_author_index"))
            await db.commit()
        before = len(await repo.ids())
        added = 0
        for i in range(0, len(entries), BATCH_SIZE):
            batch = entries[i : i + BATCH_SIZE]
            added += await repo.upsert_many(batch)
        after = len(await repo.ids())
        print(f"[sitemap] abans: {before} | afegides: {added} | total: {after}")


if __name__ == "__main__":
    asyncio.run(main())
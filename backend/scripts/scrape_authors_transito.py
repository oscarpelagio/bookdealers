"""Volcado de autoras de Editorial Tránsito a la tabla `author_source`.

La página `/autoras/` trae nombre, foto y bio de todas las autoras en un
único fetch (no hay perfiles individuales). Cada autora se guarda con
`editorial='transito'`, reutilizando el pipeline del perfil de autor.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/scrape_authors_transito.py
    docker compose exec back python scripts/scrape_authors_transito.py --limit 5
    docker compose exec back python scripts/scrape_authors_transito.py --dry-run
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.clients import TransitoClient
from app.core.db import async_session
from app.crud import AuthorSourceRepository
from app.utils import NormalizationUtils

EDITORIAL = "transito"


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Volcado de autoras de Editorial Tránsito a author_source"
    )
    parser.add_argument("--limit", type=int, default=None, help="Máximo de autoras a procesar")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en BD, solo muestra")
    args = parser.parse_args()

    client = TransitoClient()
    try:
        profiles = await client.get_authors()
    finally:
        await client.aclose()

    if args.limit is not None:
        profiles = profiles[: args.limit]

    ok = 0
    skipped = 0
    async with async_session() as db:
        repo = AuthorSourceRepository(db)
        for profile in profiles:
            author_key = NormalizationUtils.normalize_text(
                NormalizationUtils.author_name_first(profile.name)
            )
            if not author_key:
                skipped += 1
                continue
            if args.dry_run:
                print(
                    f"[dry-run] key={author_key!r} name={profile.name!r} "
                    f"img={bool(profile.image_url)} desc={bool(profile.description)}"
                )
                ok += 1
                continue
            await repo.upsert(
                author_key=author_key,
                editorial=EDITORIAL,
                name=profile.name,
                slug=None,
                description=profile.description,
                image_url=profile.image_url,
                extra=None,
            )
            ok += 1

    print(f"[transito] {len(profiles)} autoras | escritas: {ok} | skip: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
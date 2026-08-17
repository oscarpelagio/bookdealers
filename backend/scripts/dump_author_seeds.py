"""Exporta els autors-editorials i els índexs a JSON versionats (seeds).

Genera (a `backend/app/core/`):
- author_source_seed.json          -> author_source + related (1:molts) anidat
- penguin_author_index_seed.json   -> índex lleuger de Penguin
- asteroide_author_index_seed.json -> índex lleuger de Libros del Asteroide

Uso (desde el contenedor del backend, tras `alembic upgrade head`):
    docker compose exec back python scripts/dump_author_seeds.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_engine
from app.models import AsteroideAuthorIndex, AuthorSource, AuthorSourceRelated, PenguinAuthorIndex

OUT_DIR = Path(__file__).resolve().parents[1] / "app" / "core"


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


async def dump_author_source() -> int:
    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        rows = (await db.exec(select(AuthorSource).order_by(AuthorSource.editorial, AuthorSource.author_key))).all()
        related_rows = (await db.exec(select(AuthorSourceRelated).order_by(AuthorSourceRelated.author_key, AuthorSourceRelated.editorial, AuthorSourceRelated.posicion))).all()

    by_key: dict[tuple[str, str], list] = {}
    for item in related_rows:
        by_key.setdefault((item.author_key, item.editorial), []).append(
            {
                "tipo": item.tipo,
                "titulo": item.titulo,
                "url": item.url,
                "fecha": item.fecha,
                "descripcion": item.descripcion,
                "thumbnail": item.thumbnail,
                "categoria": item.categoria,
            }
        )

    payload = []
    for row in rows:
        entry = {
            "author_key": row.author_key,
            "editorial": row.editorial,
            "name": row.name,
            "slug": row.slug,
            "description": row.description,
            "image_url": row.image_url,
            "fetched_at": _iso(row.fetched_at),
        }
        related = by_key.get((row.author_key, row.editorial))
        if related:
            entry["related"] = related
        payload.append(entry)

    (OUT_DIR / "author_source_seed.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return len(payload)


async def dump_penguin_index() -> int:
    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        rows = (await db.exec(select(PenguinAuthorIndex).order_by(PenguinAuthorIndex.author_id))).all()
    payload = [
        {
            "author_id": row.author_id,
            "name": row.name,
            "name_normalized": row.name_normalized,
            "slug": row.slug,
            "thumb": row.thumb,
            "fetched_at": _iso(row.fetched_at),
        }
        for row in rows
    ]
    (OUT_DIR / "penguin_author_index_seed.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return len(payload)


async def dump_asteroide_index() -> int:
    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        rows = (await db.exec(select(AsteroideAuthorIndex).order_by(AsteroideAuthorIndex.slug))).all()
    payload = [
        {
            "slug": row.slug,
            "name": row.name,
            "name_normalized": row.name_normalized,
            "fetched_at": _iso(row.fetched_at),
        }
        for row in rows
    ]
    (OUT_DIR / "asteroide_author_index_seed.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return len(payload)


async def main() -> None:
    n_sources = await dump_author_source()
    n_penguin = await dump_penguin_index()
    n_asteroide = await dump_asteroide_index()
    print(f"[dump] author_source: {n_sources} | penguin_index: {n_penguin} | asteroide_index: {n_asteroide}")
    print(f"[dump] generat a {OUT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())

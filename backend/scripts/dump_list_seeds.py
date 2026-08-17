"""Exporta les llistes genèriques a JSON versionat (seed).

Genera (a `backend/app/core/`):
- source_list_seed.json -> sourced_lists + llibres (1:molts) anidats

Uso (desde el contenedor del backend, tras `alembic upgrade head`):
    docker compose exec back python scripts/dump_list_seeds.py
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
from app.models import SourceList, SourceListBook

OUT_DIR = Path(__file__).resolve().parents[1] / "app" / "core"


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


async def dump_source_lists() -> int:
    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        rows = (
            await db.exec(
                select(SourceList).order_by(SourceList.source, SourceList.slug)
            )
        ).all()
        book_rows = (
            await db.exec(
                select(SourceListBook).order_by(
                    SourceListBook.list_id, SourceListBook.posicion
                )
            )
        ).all()

    by_list: dict[int, list] = {}
    for item in book_rows:
        by_list.setdefault(item.list_id, []).append(
            {
                "posicion": item.posicion,
                "titulo_normalizado": item.titulo_normalizado,
                "autor_normalizado": item.autor_normalizado,
                "book_id": item.book_id,
            }
        )

    payload = []
    for row in rows:
        entry = {
            "source": row.source,
            "slug": row.slug,
            "url": row.url,
            "tipo": row.tipo,
            "titulo": row.titulo,
            "subtitulo": row.subtitulo,
            "intro": row.intro,
            "autor": row.autor,
            "fecha": row.fecha,
            "cuerpo": row.cuerpo,
            "portada_url": row.portada_url,
            "status": row.status,
            "fetched_at": _iso(row.fetched_at),
        }
        books = by_list.get(row.id)
        if books:
            entry["books"] = books
        payload.append(entry)

    (OUT_DIR / "source_list_seed.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return len(payload)


async def main() -> None:
    n = await dump_source_lists()
    print(f"[dump] source_lists: {n} | generat a {OUT_DIR / 'source_list_seed.json'}")


if __name__ == "__main__":
    asyncio.run(main())
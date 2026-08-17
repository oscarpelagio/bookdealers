"""Seed de llistes genèriques de fonts web a l'arrencada de l'app.

Llegeix `source_list_seed.json` de `backend/app/core/` i fa un upsert
idempotent (mateix patró que `seed_author_data`):

- `source_list_seed.json` -> `sourced_lists` (+ `sourced_list_books`)

Estratègia híbrida:
- A l'arrencada es bolquen totes les llistes del seed (ON CONFLICT DO NOTHING
  per (source, slug)) amb els seus llibres.
- A la consulta (`GET /source-lists/{slug}`) si una llista no existeix encara a
  la BD, es crea des del JSON (materialització perezosa) amb web+autor+foto+llibres.

El seed no esborra res: les llistes consultades i modificades a mà es conserven.
"""

import json
from datetime import datetime
from pathlib import Path

from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_engine
from app.crud import SourceListRepository
from app.models import SourceList

_SEED_FILE = "source_list_seed.json"

_BATCH = 1000

_cache: list | None = None


def _resolve_json_path(filename: str) -> Path | None:
    candidates = [
        # Ruta dins del contenidor docker (compose munta ./backend:/app).
        Path("/app/app/core") / filename,
        # Ruta des d'una execució local al repo.
        Path(__file__).resolve().parent / filename,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load(filename: str) -> list | None:
    global _cache
    if _cache is not None:
        return _cache
    path = _resolve_json_path(filename)
    if path is None:
        print(f"[source_list_seed] No es troba {filename}; seed omès.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        print(f"[source_list_seed] {filename} buit; seed omès.")
        return None
    _cache = data
    return data


async def _seed_source_lists() -> None:
    data = _load(_SEED_FILE)
    if data is None:
        return

    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        repo = SourceListRepository(db)
        for i in range(0, len(data), _BATCH):
            chunk = data[i : i + _BATCH]
            rows = [
                {
                    "source": row["source"],
                    "slug": row["slug"],
                    "url": row["url"],
                    "tipo": row.get("tipo"),
                    "titulo": row["titulo"],
                    "subtitulo": row.get("subtitulo"),
                    "intro": row.get("intro"),
                    "autor": row.get("autor"),
                    "fecha": row.get("fecha"),
                    "cuerpo": row.get("cuerpo"),
                    "portada_url": row.get("portada_url"),
                    "status": row.get("status") or "done",
                    "fetched_at": datetime.fromisoformat(row["fetched_at"])
                    if row.get("fetched_at")
                    else datetime.utcnow(),
                }
                for row in chunk
            ]
            await repo.bulk_upsert(rows)
        # Després de bolcar les llistes, bolca els llibres de cada entrada del
        # seed (idempotent per (list_id, posicion), preservant book_id resolts).
        for row in data:
            books = [
                {
                    "posicion": b["posicion"],
                    "titulo_normalizado": b["titulo_normalizado"],
                    "autor_normalizado": b["autor_normalizado"],
                    "book_id": b.get("book_id"),
                }
                for b in row.get("books", [])
            ]
            if books:
                await repo.bulk_upsert_books(row["source"], row["slug"], books)
    print(f"[source_list_seed] sourced_lists carregat ({len(data)} llistes).")


async def seed_source_list_data() -> None:
    """Volca el JSON de llistes genèriques a la BD (upsert idempotent)."""
    await _seed_source_lists()


async def materialize_source_list(source: str, slug: str) -> SourceList | None:
    """Crea una llista des del seed JSON si encara no existeix (perezosa).

    Retorna la llista creada, o `None` si no hi és al JSON o ja existia.
    """
    data = _load(_SEED_FILE)
    if data is None:
        return None
    for row in data:
        if row.get("source") == source and row.get("slug") == slug:
            async with AsyncSession(async_engine, expire_on_commit=False) as db:
                repo = SourceListRepository(db)
                existing = await repo.get_by_slug(slug, source)
                if existing is not None:
                    return existing
                slist = SourceList(
                    source=row["source"],
                    slug=row["slug"],
                    url=row["url"],
                    tipo=row.get("tipo"),
                    titulo=row["titulo"],
                    subtitulo=row.get("subtitulo"),
                    intro=row.get("intro"),
                    autor=row.get("autor"),
                    fecha=row.get("fecha"),
                    cuerpo=row.get("cuerpo"),
                    portada_url=row.get("portada_url"),
                    status=row.get("status") or "done",
                    fetched_at=datetime.fromisoformat(row["fetched_at"])
                    if row.get("fetched_at")
                    else datetime.utcnow(),
                )
                books = [
                    {
                        "posicion": b["posicion"],
                        "titulo_normalizado": b["titulo_normalizado"],
                        "autor_normalizado": b["autor_normalizado"],
                        "book_id": b.get("book_id"),
                    }
                    for b in row.get("books", [])
                ]
                return await repo.create_from_seed(slist, books)
    return None
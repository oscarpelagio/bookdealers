"""Seed d'autors-editorials a l'arrencada de l'app.

Llegeix els JSON versionats de `backend/app/core/` i fa un upsert idempotent
(mateix patró que `seed_catalogs`):
- `author_source_seed.json`          -> `author_source` (+ `author_source_related`)
- `penguin_author_index_seed.json`   -> `penguin_author_index`
- `asteroide_author_index_seed.json` -> `asteroide_author_index`

El seed no esborra res: els autors consultats i afegits peresosament a la BD
es conserven; els del volcat es mantenen actualitzats.
"""

import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_engine
from app.crud import AuthorSourceRelatedRepository, AuthorSourceRepository
from app.models import AsteroideAuthorIndex, PenguinAuthorIndex

_SEED_FILES = {
    "author_source": "author_source_seed.json",
    "penguin_index": "penguin_author_index_seed.json",
    "asteroide_index": "asteroide_author_index_seed.json",
}

_BATCH = 1000


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
    path = _resolve_json_path(filename)
    if path is None:
        print(f"[author_seed] No es troba {filename}; seed omès.")
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        print(f"[author_seed] {filename} buit; seed omès.")
        return None
    return data


async def _seed_author_source() -> None:
    data = _load(_SEED_FILES["author_source"])
    if data is None:
        return

    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        repo = AuthorSourceRepository(db)
        related_repo = AuthorSourceRelatedRepository(db)
        for i in range(0, len(data), _BATCH):
            chunk = data[i : i + _BATCH]
            await repo.bulk_upsert(
                [
                    {
                        "author_key": row["author_key"],
                        "editorial": row["editorial"],
                        "name": row["name"],
                        "slug": row.get("slug"),
                        "description": row.get("description"),
                        "image_url": row.get("image_url"),
                        "fetched_at": datetime.fromisoformat(row["fetched_at"])
                        if row.get("fetched_at")
                        else datetime.utcnow(),
                    }
                    for row in chunk
                ]
            )
            for row in chunk:
                await related_repo.replace(
                    row["author_key"], row["editorial"], row.get("related")
                )
    print(f"[author_seed] author_source carregat ({len(data)} autors).")


async def _seed_penguin_index() -> None:
    data = _load(_SEED_FILES["penguin_index"])
    if data is None:
        return

    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        for i in range(0, len(data), _BATCH):
            chunk = data[i : i + _BATCH]
            rows = [
                {
                    "author_id": row["author_id"],
                    "name": row["name"],
                    "name_normalized": row["name_normalized"],
                    "slug": row["slug"],
                    "thumb": row.get("thumb"),
                    "fetched_at": datetime.fromisoformat(row["fetched_at"])
                    if row.get("fetched_at")
                    else datetime.utcnow(),
                }
                for row in chunk
            ]
            stmt = insert(PenguinAuthorIndex).values(rows).on_conflict_do_nothing()
            await db.execute(stmt)
        await db.commit()
    print(f"[author_seed] penguin_author_index carregat ({len(data)} entrades).")


async def _seed_asteroide_index() -> None:
    data = _load(_SEED_FILES["asteroide_index"])
    if data is None:
        return

    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        for i in range(0, len(data), _BATCH):
            chunk = data[i : i + _BATCH]
            rows = [
                {
                    "slug": row["slug"],
                    "name": row["name"],
                    "name_normalized": row["name_normalized"],
                    "fetched_at": datetime.fromisoformat(row["fetched_at"])
                    if row.get("fetched_at")
                    else datetime.utcnow(),
                }
                for row in chunk
            ]
            stmt = insert(AsteroideAuthorIndex).values(rows).on_conflict_do_nothing()
            await db.execute(stmt)
        await db.commit()
    print(f"[author_seed] asteroide_author_index carregat ({len(data)} entrades).")


async def seed_author_data() -> None:
    """Volca els JSON d'autors-editorials a la BD (upsert idempotent)."""
    await _seed_author_source()
    await _seed_penguin_index()
    await _seed_asteroide_index()

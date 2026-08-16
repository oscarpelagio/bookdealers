"""Script puntual: importa el CSV de Goodreads (goodreads_library_export.csv)
usant el mateix wiring que l'endpoint /goodreads-csv per verificar que el
pipeline funciona (cerca Z39.50, inserció de llibres, caché de cerca).

Ús: docker compose exec -T back python scripts/import_goodreads_verify.py [limit]
El CSV s'ha de copiar prèviament a /tmp del contenidor:
  docker cp goodreads_library_export.csv back:/tmp/goodreads_library_export.csv
"""

import asyncio
import io
import sys

from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.adapters import Z3950SearchAdapter
from app.clients import Z3950ImportClient
from app.core.db import async_engine
from app.crud import BookRepository, SearchRepository, CatalogRepository
from app.services import Z3950SearchService
from app.utils import CsvUtils

CSV_PATH = "/tmp/goodreads_library_export.csv"


async def main() -> None:
    with open(CSV_PATH, "rb") as f:
        data = f.read()
    upload = UploadFile(file=io.BytesIO(data), filename="goodreads_library_export.csv")

    rows = await CsvUtils.parse_goodreads_book(upload)
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if limit:
        rows = rows[:limit]

    async with AsyncSession(async_engine, expire_on_commit=False) as db:
        service = Z3950SearchService(
            BookRepository(db),
            SearchRepository(db),
            CatalogRepository(db),
            Z3950ImportClient(),
            Z3950SearchAdapter(),
        )
        ok = []
        for row in rows:
            try:
                saved = await service.search_and_process(
                    row["title"], row["author"], "aladi", max_results=1
                )
                if saved:
                    ok.append((saved[0], row.get("exclusive_shelf")))
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR {row['title']!r}: {exc}")
        print(f"== IMPORTADOS {len(ok)} de {len(rows)} ==")
        for book, shelf in ok:
            print("-", book.id, "|", book.title, "|", book.author, "| shelf:", shelf)


if __name__ == "__main__":
    asyncio.run(main())
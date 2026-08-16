"""Scraping del blog de La Central (categoria temàtiques, 532 articles).

Fase A: recorre els llistats `?pg=1..N` (12 per pàgina) i crea les files
pendents a `central_blog_article`.
Fase B: descarrega cada article en paral·lel (`--concurrency`, per defecte 8,
a fuego), el guarda amb els seus llibres a `central_blog_article_book` i el
marca com a `done`.

Reeniable: reexecució salta els articles ja fets. Els 403/429 tenen backoff
exponencial al client.

Uso (desde el contenedor del backend):
    docker compose exec back python scripts/scrape_la_central_articles.py
    docker compose exec back python scripts/scrape_la_central_articles.py --resume
    docker compose exec back python scripts/scrape_la_central_articles.py --limit 32 --concurrency 8
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.adapters.la_central_adapter import parse_article, parse_listing
from app.clients.la_central_client import LaCentralClient
from app.core.db import async_session
from app.crud.central_article_repository import CentralArticleRepository

MAX_PAGES = 60


async def scrape_listings(client: LaCentralClient, repo: CentralArticleRepository) -> int:
    """Fase A: llistats → files pendents. Retorna el nombre de pàgines llegides."""
    sem = asyncio.Semaphore(4)
    pg = 0
    created = 0

    async def fetch_and_store(p: int) -> int:
        async with sem:
            html = await client.get_listing(p)
        cards = parse_listing(html)
        if not cards:
            return 0
        return await repo.upsert_cards(cards)

    while pg < MAX_PAGES:
        pg += 1
        try:
            added = await fetch_and_store(pg)
        except RuntimeError as e:
            print(f"[fase A] aturada a pg={pg}: {e}")
            break
        created += added
        if added < 12:
            print(f"[fase A] últim llistat parcial a pg={pg} ({added}/12). Fi.")
            break
        if pg == 1 or pg % 5 == 0:
            print(f"[fase A] pg={pg} nous fins ara: {created}")

    print(f"[fase A] {pg} llistats | nous: {created}")
    return created


async def _scrape_one(client: LaCentralClient, slug: str) -> tuple[str, int, str | None]:
    """Scrapeja un article i el desa. Retorna (slug, n_libros, error)."""
    try:
        html = await client.get_article(slug)
        article = parse_article(html, slug)
        async with async_session() as db:
            n_books = await CentralArticleRepository(db).save_article(article, article.libros)
        return slug, n_books, None
    except RuntimeError as e:
        return slug, 0, str(e)


async def run(limit: int | None, concurrency: int, resume: bool) -> None:
    client = LaCentralClient(concurrency=concurrency)
    try:
        async with async_session() as db:
            repo = CentralArticleRepository(db)

            if resume:
                total, done = await repo.count()
                print(f"[stats] previs: {total} articles, {done} fets")

            print("=== FASE A: llistats ===")
            await scrape_listings(client, repo)

            print("=== FASE B: articles ===")
            pending = await repo.pending_articles()
            if not pending:
                print("[fase B] cap article pendent.")
                return
            if limit:
                pending = pending[:limit]

            sem = asyncio.Semaphore(client.concurrency)
            done_counter = 0
            ok = failed = n_books_total = 0

            async def worker(slug: str) -> tuple[str, int, str | None]:
                async with sem:
                    return await _scrape_one(client, slug)

            tasks = [asyncio.create_task(worker(a.slug)) for a in pending]
            batch = 32
            i = 0
            while tasks:
                chunk = tasks[:batch]
                tasks = tasks[batch:]
                results = await asyncio.gather(*chunk)
                for slug, n_books, error in results:
                    i += 1
                    if error:
                        failed += 1
                        print(f"  [fail] {i}/{len(pending)} {slug}: {error}")
                    else:
                        ok += 1
                        n_books_total += n_books
            total, done = await repo.count()
            print(
                f"\n=== RESULTAT === ok={ok} fail={failed} llibres={n_books_total} "
                f"| BD: {done}/{total}"
            )
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraping del blog de La Central (temàtiques)"
    )
    parser.add_argument("--limit", type=int, default=None, help="Màxim d'articles a processar (fase B)")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrència (a fuego)")
    parser.add_argument("--resume", action="store_true", help="Reexecuta només els pendents")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.concurrency, args.resume))


if __name__ == "__main__":
    main()
"""Servei de volcat d'autors d'Anagrama (agressiu, multi-worker).

- Recull tots els slugs dels 26 índexs alfabètics.
- Descarrega i parseja els perfils en paral·lel (semàfor amb `workers`).
- Si el servidor respon 429/403 (too many requests) avisa en stderr i
  ralentitza de forma adaptativa sense perdre el volcat.
- Escriu directament a `author_source` (+ `author_source_related`) amb
  `editorial='anagrama'`. Reanudable: salta els slugs ja descarregats
  tret de `refresh=True`.
"""

import asyncio
import time
from dataclasses import dataclass, field

from app.clients.anagrama_client import AnagramaClient, RateLimitedError
from app.crud import AuthorSourceRelatedRepository, AuthorSourceRepository
from app.utils import NormalizationUtils

LETTERS = "abcdefghijklmnopqrstuvwxyz"
EDITORIAL = "anagrama"


@dataclass
class ScrapeStats:
    ok: int = 0
    rate_limited: int = 0
    failed: int = 0
    with_photo: int = 0
    with_extra: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    elapsed: float = 0.0


class AnagramaScraperService:
    """Orquestador del volcat: índexs → perfils → `author_source`.

    Cada worker obre la seva pròpia sessió perquè `AsyncSession` no és segura
    per a ús concurrent entre tasques.
    """

    def __init__(
        self,
        client: AnagramaClient,
        session_factory,
        workers: int = 8,
    ):
        self.client = client
        self.session_factory = session_factory
        self.workers = workers
        self._throttle_until: float = 0.0
        self._lock = asyncio.Lock()
        self._consecutive_rate = 0

    # ------------------------------------------------------------------ #
    # Rate limiting adaptatiu
    # ------------------------------------------------------------------ #
    async def _throttle(self, seconds: float) -> None:
        async with self._lock:
            target = time.monotonic() + seconds
            if target > self._throttle_until:
                self._throttle_until = target

    async def _wait_if_throttled(self) -> None:
        while True:
            async with self._lock:
                remaining = self._throttle_until - time.monotonic()
            if remaining <= 0:
                return
            await asyncio.sleep(min(remaining, 2.0))

    def _notify_rate_limit(self, slug: str, detail: str) -> None:
        self._consecutive_rate += 1
        backoff = 30 * self._consecutive_rate
        print(
            f"\n!!! TOO MANY REQUESTS en {slug}: {detail} — ralentizando "
            f"{backoff}s (consecutivo #{self._consecutive_rate}) !!!",
            flush=True,
        )
        self._throttle(backoff)

    # ------------------------------------------------------------------ #
    # Recol·lecció de slugs
    # ------------------------------------------------------------------ #
    async def collect_slugs(self, letters: str = LETTERS) -> list[str]:
        slugs: set[str] = set()
        for letter in letters:
            try:
                slugs.update(await self.client.get_letter_index(letter))
            except RateLimitedError as exc:
                self._notify_rate_limit(f"/autores/{letter}", str(exc))
                slugs.update(await self.client.get_letter_index(letter))
        return sorted(slugs)

    # ------------------------------------------------------------------ #
    # Volcat
    # ------------------------------------------------------------------ #
    async def scrape(
        self,
        limit: int | None = None,
        refresh: bool = False,
        letters: str | None = None,
        progress_every: int = 50,
    ) -> ScrapeStats:
        start = time.monotonic()
        letters = letters or LETTERS
        slugs = await self.collect_slugs(letters)
        if not refresh:
            async with self.session_factory() as db:
                fetched = await AuthorSourceRepository(db).slugs_for_editorial(EDITORIAL)
            pending = [s for s in slugs if s not in fetched]
        else:
            pending = list(slugs)
        if limit is not None:
            pending = pending[:limit]

        total = len(pending)
        stats = ScrapeStats()
        print(f"[anagrama] {len(slugs)} autores en índexs | a processar: {total}", flush=True)

        semaphore = asyncio.Semaphore(self.workers)

        async def process(slug: str, repo: AuthorSourceRepository, related_repo: AuthorSourceRelatedRepository) -> None:
            await self._wait_if_throttled()
            try:
                profile = await self.client.get_profile(slug)
            except RateLimitedError as exc:
                self._notify_rate_limit(slug, str(exc))
                stats.rate_limited += 1
                # reintento una vegada per slug per no perdre dades
                await self._wait_if_throttled()
                try:
                    profile = await self.client.get_profile(slug)
                except Exception as exc2:
                    stats.failed += 1
                    stats.failures.append((slug, repr(exc2)))
                    return
            except Exception as exc:
                stats.failed += 1
                stats.failures.append((slug, repr(exc)))
                return

            author_key = NormalizationUtils.normalize_text(
                NormalizationUtils.author_name_first(profile.name)
            )
            if not author_key:
                stats.failed += 1
                stats.failures.append((slug, "author_key buit"))
                return

            await repo.upsert(
                author_key=author_key,
                editorial=EDITORIAL,
                name=profile.name,
                slug=slug,
                description=profile.description,
                image_url=profile.image_url,
            )
            await related_repo.replace(author_key, EDITORIAL, profile.extra or None)
            stats.ok += 1
            if profile.image_url:
                stats.with_photo += 1
            if profile.extra:
                stats.with_extra += 1

        queue: asyncio.Queue[str] = asyncio.Queue()
        done = 0
        done_lock = asyncio.Lock()

        async def worker() -> None:
            nonlocal done
            async with self.session_factory() as db:
                repo = AuthorSourceRepository(db)
                related_repo = AuthorSourceRelatedRepository(db)
                while True:
                    slug = await queue.get()
                    try:
                        async with semaphore:
                            await process(slug, repo, related_repo)
                    finally:
                        queue.task_done()
                        async with done_lock:
                            done += 1
                            if done % progress_every == 0 or done == total:
                                print(
                                    f"[anagrama] {done}/{total} | ok={stats.ok} "
                                    f"fail={stats.failed} rate={stats.rate_limited}",
                                    flush=True,
                                )
        for slug in pending:
            queue.put_nowait(slug)

        tasks = [asyncio.create_task(worker()) for _ in range(self.workers)]
        await queue.join()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        stats.elapsed = time.monotonic() - start
        return stats
"""Client HTTP per al blog de La Central.

La Central està darrere de Cloudflare: `httpx`/`urllib` reben 403. Aquest
client fa servir `curl_cffi` amb fingerprint de Chrome (`impersonate`), que sí
travessa el challenge. Inclou reintents amb backoff exponencial per no petar
en pics de 403/429.
"""

import asyncio
import random

from curl_cffi import requests as cr
from curl_cffi.requests import AsyncSession

LISTING_URL = "https://www.lacentral.com/blog/tipo/tematicas"
ARTICLE_URL = "https://www.lacentral.com/blog"

_TIMEOUT = 30.0
_MAX_ATTEMPTS = 4
_BASE_BACKOFF = 2.0


class LaCentralClient:
    """Fetch de llistats i articles del blog de La Central."""

    def __init__(self, concurrency: int = 8):
        self.concurrency = concurrency
        self._session: AsyncSession | None = None
        self._semaphore = asyncio.Semaphore(concurrency)

    async def _get_session(self) -> AsyncSession:
        if self._session is None:
            self._session = cr.AsyncSession(
                impersonate="chrome",
                timeout=_TIMEOUT,
                headers={
                    "Accept-Language": "ca,es;q=0.9,en;q=0.8",
                    "Referer": "https://www.lacentral.com/",
                },
            )
        return self._session

    async def _get_html(self, url: str) -> str:
        session = await self._get_session()
        attempt = 0
        while True:
            async with self._semaphore:
                response = await session.get(url)
            if response.status_code == 200:
                return response.text
            attempt += 1
            if attempt >= _MAX_ATTEMPTS:
                raise RuntimeError(
                    f"La Central {response.status_code} després de {_MAX_ATTEMPTS} intents: {url}"
                )
            delay = _BASE_BACKOFF * (2 ** (attempt - 1)) + random.uniform(0.2, 0.8)
            print(f"  [retry {attempt}/{_MAX_ATTEMPTS}] {response.status_code} esperant {delay:.1f}s {url}")
            await asyncio.sleep(delay)

    async def get_listing(self, pg: int) -> str:
        url = LISTING_URL if pg <= 1 else f"{LISTING_URL}?pg={pg}"
        return await self._get_html(url)

    async def get_article(self, slug: str) -> str:
        return await self._get_html(f"{ARTICLE_URL}/{slug}")

    async def close(self) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
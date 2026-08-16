"""Client HTTP per a blackiebooks.org (REST API de WordPress).

S'usa `/wp-json/wp/v2/autor` en lloc de les pàgines HTML: el servidor
bloqueja (403) les pàgines HTML des de xarxes no nadiues, mentre que la
REST API respon sense problemes i exposa el mateix contingut.
"""

import httpx

from app.adapters import BlackieProfile
from app.adapters.blackie_adapter import (
    parse_authors_index,
    parse_media_url,
    parse_profile,
)

API = "https://blackiebooks.org/wp-json/wp/v2"
PER_PAGE = 100


class RateLimitedError(RuntimeError):
    """El servidor ha respost 429/403 (too many requests / bloqueig)."""


class BlackieClient:
    """Fetch dels autors de Blackie Books via REST API.

    Un únic `httpx.AsyncClient` compartit (keep-alive) per tots els workers.
    Llança `RateLimitedError` quan detecta 429/403 perquè el servei avisi i
    ralenteixi.
    """

    def __init__(self, timeout: float = 90.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                # IMPORTANT: un User-Agent de navegador complet fa que el WAF
                # respongui 403. El genèric "Mozilla/5.0" passa i la REST API
                # respon (lentament: 4-7s per pàgina).
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8,en;q=0.7",
            },
        )

    async def _get_json(self, url: str) -> dict | list:
        response = await self.client.get(url)
        if response.status_code in (429, 403):
            raise RateLimitedError(
                f"HTTP {response.status_code} en {url} — too many requests"
            )
        response.raise_for_status()
        return response.json()

    async def get_authors_index(self) -> list[str]:
        """Recoge los slugs de todos los autores (paginado)."""
        slugs: list[str] = []
        page = 1
        while True:
            items = await self._get_json(f"{API}/autor?per_page={PER_PAGE}&page={page}")
            if not items:
                break
            slugs += parse_authors_index(items)
            if len(items) < PER_PAGE:
                break
            page += 1
        return slugs

    async def get_profile(self, slug: str) -> BlackieProfile:
        items = await self._get_json(f"{API}/autor?slug={slug}")
        if not items:
            return BlackieProfile(name="")
        profile = parse_profile(items[0])
        if profile.media_id is not None:
            media = await self._get_json(f"{API}/media/{profile.media_id}")
            profile.image_url = parse_media_url(media)
        return profile

    async def aclose(self) -> None:
        await self.client.aclose()
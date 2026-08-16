"""Client HTTP para anagrama-ed.es (índice de autores y perfiles)."""

import httpx

from app.adapters import AnagramaProfile
from app.adapters.anagrama_adapter import parse_letter_index, parse_profile

BASE_URL = "https://www.anagrama-ed.es"


class RateLimitedError(RuntimeError):
    """El servidor ha respondido 429/403 (too many requests / bloqueo Cloudflare)."""


class AnagramaClient:
    """Fetch de las páginas de autores de Anagrama.

    Un único `httpx.AsyncClient` compartido (keep-alive) por todos los workers.
    Lanza `RateLimitedError` cuando detecta 429/403 para que el servicio
    avise y ralentice.
    """

    def __init__(self, timeout: float = 30.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8,en;q=0.7",
            },
        )

    async def _get(self, url: str) -> str:
        response = await self.client.get(url)
        if response.status_code in (429, 403):
            raise RateLimitedError(
                f"HTTP {response.status_code} en {url} — too many requests"
            )
        response.raise_for_status()
        return response.text

    async def get_letter_index(self, letter: str) -> list[str]:
        html = await self._get(f"{BASE_URL}/autores/{letter}")
        return parse_letter_index(html)

    async def get_profile(self, slug: str) -> AnagramaProfile:
        html = await self._get(f"{BASE_URL}{slug}")
        return parse_profile(html)

    async def aclose(self) -> None:
        await self.client.aclose()

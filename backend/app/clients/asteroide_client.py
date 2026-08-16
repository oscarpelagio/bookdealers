"""Client HTTP para librosdelasteroide.com (índice de autores y perfiles)."""

import httpx

from app.adapters import AsteroideIndexEntry, AsteroideProfile
from app.adapters.asteroide_adapter import parse_authors_index, parse_profile

BASE_URL = "https://librosdelasteroide.com"
AUTORES_URL = f"{BASE_URL}/autores"


class AsteroideClient:
    """Fetch del índice de autores y de los perfiles de Libros del Asteroide."""

    def __init__(self, timeout: float = 30.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 "
                    "Safari/537.36"
                ),
                "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8,en;q=0.7",
            },
        )

    async def _get_html(self, url: str) -> str:
        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

    async def get_authors_index(self) -> list[AsteroideIndexEntry]:
        html = await self._get_html(AUTORES_URL)
        return parse_authors_index(html)

    async def get_profile(self, slug: str) -> AsteroideProfile:
        html = await self._get_html(f"{BASE_URL}/autor/{slug}")
        return parse_profile(html)

    async def aclose(self) -> None:
        await self.client.aclose()
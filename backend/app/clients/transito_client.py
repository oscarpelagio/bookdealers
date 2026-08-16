"""Client HTTP para editorialtransito.es (página de autoras, una sola llamada)."""

import httpx

from app.adapters import TransitoProfile
from app.adapters.transito_adapter import parse_authors_page

AUTORAS_URL = "https://editorialtransito.es/autoras/"


class TransitoClient:
    """Fetch de la página `/autoras/` de Editorial Tránsito."""

    def __init__(self, timeout: float = 60.0):
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8,en;q=0.7",
            },
        )

    async def get_authors(self) -> list[TransitoProfile]:
        response = await self.client.get(AUTORAS_URL)
        response.raise_for_status()
        return parse_authors_page(response.text)

    async def aclose(self) -> None:
        await self.client.aclose()
"""Client HTTP para Penguin Libros (penguinlibros.com).

Dos operaciones:
- `search_author(name)`: resuelve un autor por nombre vía el cercador
  Elastico (JSON) de Penguin.
- `get_profile(author_id, slug)`: descarga la página del perfil.

Lanza `RateLimitedError` (definido en el cliente de Anagrama) en 429/403
para que el servicio avise y ralentice.
"""

import asyncio
import json

import httpx

from app.adapters import PenguinAuthor, PenguinIndexEntry
from app.adapters.penguin_adapter import (
    ELASTICO_URL,
    parse_author_index,
    parse_author_search,
    parse_profile,
)
from app.clients.anagrama_client import RateLimitedError


class PenguinClient:
    """Fetch de páginas y búsquedas de autores de Penguin."""

    def __init__(self, timeout: float = 30.0, min_delay: float = 0.0):
        self.min_delay = min_delay
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
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.penguinlibros.com",
                "Referer": "https://www.penguinlibros.com/es/5-los-mejores-autores",
            },
        )

    async def _get(
        self,
        url: str,
        params: dict | None = None,
        method: str = "GET",
        data: dict | None = None,
    ) -> str:
        if method == "POST":
            if self.min_delay:
                await asyncio.sleep(self.min_delay)
            response = await self.client.post(url, params=params, data=data)
        else:
            response = await self.client.get(url, params=params)
        if response.status_code in (429, 403):
            raise RateLimitedError(
                f"HTTP {response.status_code} en {url} — too many requests"
            )
        response.raise_for_status()
        return response.text

    async def search_author(self, name: str, limit: int = 5) -> list[PenguinAuthor]:
        """Resuelve autores por nombre vía el endpoint Elastico (JSON)."""
        text = await self._get(
            ELASTICO_URL,
            {
                "s": "autores",
                "q": name,
                "resultsPerPage": limit,
                "ajax": "true",
                "searchType": "autores",
            },
        )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        return parse_author_search(payload)

    async def get_index_page(self, page_no: int = 1) -> list[PenguinIndexEntry]:
        """Descarga y parsea una página del índice de autores vía el endpoint
        AJAX del módulo (`?fc=module&module=penguinlibros`, action
        `showAuthorsTematica`). El `pageno` por GET se ignora para bots; el
        endpoint POST devuelve JSON con `products` (HTML) + `productsCount`."""
        text = await self._get(
            "https://www.penguinlibros.com/es/?fc=module&module=penguinlibros",
            params={},
            method="POST",
            data={
                "ajax": "true",
                "controller": "letters",
                "action": "showAuthorsTematica",
                "dataType": "json",
                "listaTematicasHijas": "",
                "listaFormatos": "",
                "tematica": "5",
                "limit": "12",
                "ob": "fecha_nov",
                "pageno": str(page_no),
                "ow": "desc",
                "op": "grid",
                "letra": "",
                "idCategory": "5",
            },
        )
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return []
        products = payload.get("products") or ""
        return parse_author_index(products)

    async def get_profile(self, author_id: int, slug: str | None = None) -> str:
        """Descarga la página del perfil de un autor."""
        path = f"/es/{author_id}"
        if slug:
            path += f"-{slug}"
        return await self._get(f"https://www.penguinlibros.com{path}")

    async def aclose(self) -> None:
        await self.client.aclose()
"""Client per a la API de Google Books amb patró Singleton."""

import httpx

from app.core.config import settings

class GoogleBooksClient:
    """Client per a la API de Google Books amb reuse de connexions HTTP."""
    
    BASE_URL = "https://www.googleapis.com/books/v1/volumes"
    _client: httpx.AsyncClient | None = None


    def __init__(self):
        """Inicialitza el client amb la API key de configuració."""
        self.api_key = settings.google_api_key

    @property
    def client(self) -> httpx.AsyncClient:
        """Retorna el client HTTP, creant-lo si és necessari."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client

    async def close(self):
        """Tanca el client HTTP de manera segura."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def search_books(self, query: str, max_results: int = 10, order : str = "relevance") -> dict:
        """
        Cerca llibres a Google Books API.
        """
        params = {
            "q": query, 
            "maxResults": max(1, min(max_results, 10)),
            "orderBy": order
        }
        params["key"] = self.api_key
        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()

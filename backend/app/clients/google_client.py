"""Client for the Google Books API with connection reuse."""

from app.core.config import settings
from .search_base_client import SearchBaseClient

class GoogleBooksClient(SearchBaseClient):
    """Client for the Google Books API with HTTP connection reuse."""
    
    BASE_URL = "https://www.googleapis.com/books/v1/volumes"

    def __init__(self):
        """Initialize the client with the configured API key."""
        super().__init__()
        self.api_key = settings.google_api_key

    async def fetch_books(self, params: dict) -> dict:
        """Search books using the Google Books API."""
        query = params.get("query") or ""
        max_results = params.get("max_results", 10)
        order = params.get("order", "relevance")
        request_params = {
            "q": query,
            "maxResults": max(1, min(max_results, 10)),
            "orderBy": order,
        }
        request_params["key"] = self.api_key
        response = await self.client.get(self.BASE_URL, params=request_params)
        response.raise_for_status()
        return response.json()

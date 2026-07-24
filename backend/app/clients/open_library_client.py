from .search_base_client import SearchBaseClient


class OpenLibraryClient(SearchBaseClient):
    BASE_URL = "https://openlibrary.org/search.json"

    def __init__(self) -> None:
        super().__init__()

    async def fetch_books(self, params: dict) -> dict:
        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        return response.json()

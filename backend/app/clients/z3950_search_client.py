"""Client for the Z39.50 microservice search endpoint (general user search)."""

import httpx

from .search_base_client import SearchBaseClient


class Z3950SearchClient(SearchBaseClient):

    async def fetch_books(self, params: dict) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://z3950:8001/search-brief", params=params
            )
            response.raise_for_status()
            return response.text

    async def fetch_books_author(self, params: dict) -> str:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://z3950:8001/search-author", params=params
            )
            response.raise_for_status()
            return response.text

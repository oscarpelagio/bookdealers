"""Client for the photo-scraper microservice (Google Images headless)."""

import httpx


class GooglePhotoClient:

    async def fetch_photo(self, author: str) -> dict:
        async with httpx.AsyncClient(timeout=40.0) as client:
            response = await client.get(
                "http://photo-scraper:8002/photo-search/image", params={"author": author}
            )
            response.raise_for_status()
            return response.json()
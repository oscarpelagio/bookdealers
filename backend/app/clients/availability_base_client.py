from abc import ABC, abstractmethod
from app.schemas import FetchRequest
import httpx

class AvailabilityBaseClient(ABC):

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0, 
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
        )
    
    async def fetch_books(self, request: FetchRequest) -> dict:
        
        response = await self.client.get(request.url, params=request.params)
        response.raise_for_status()
        
        return response.json()
    
    async def close(self):
        await self.client.aclose()

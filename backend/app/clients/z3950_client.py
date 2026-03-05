import httpx

class Z3950Client:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search_z3950(self, title: str, author: str):
        # Reutilizamos el cliente abierto
        response = await self.client.get(
            "http://z3950:8001/search",
            params={"title": title, "author": author}
        )
        response.raise_for_status()
        return response.json()

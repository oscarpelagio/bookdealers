import httpx

class Z3950Client:
    
    async def search_z3950(self, title: str, author: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://z3950:8001/search",
                params={"title": title, "author": author},
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

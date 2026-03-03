from ..clients import Client

class Service:
    def __init__(
        self, 
        client: Client,
    ):
        self.client = client

    async def search_book(self, title, author) -> str :
        return await self.client.fetch_book(title, author)

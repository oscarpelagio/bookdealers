from ..clients import Client


class Service:
    """Capa de servicio: delega en el cliente Playwright."""

    def __init__(self, client: Client) -> None:
        self.client = client

    async def search_image(self, author: str) -> dict:
        return await self.client.search_image(author)
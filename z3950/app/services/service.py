from ..clients import Client
import re

class Service:
    def __init__(
        self, 
        client: Client,
    ):
        self.client = client

    async def search_book(self, title: str, author: str, url: str, port: int, base: str) -> str :
        return await self.client.fetch_book(self.normalize_MARC(title), author, url, port, base)

    @staticmethod
    def normalize_MARC(title) -> str:
        article_pattern = r'^(el |la |los |las |un |una |unos |unas |els |les |the |a |an |le |un |une |des |l[\'’])'
        
        title_without_article = re.sub(article_pattern, '', title, flags=re.IGNORECASE)
        
        return title_without_article.strip()

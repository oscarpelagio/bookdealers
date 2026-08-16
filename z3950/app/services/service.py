from ..clients import Client
import re

class Service:
    def __init__(
        self, 
        client: Client,
    ):
        self.client = client

    async def search_book(self, title: str, author: str, url: str, port: int, base: str) -> str :
        title = self.normalize_MARC(title)
        words = (author or "").strip().split()
        last_raw = ""
        # 1r try con la última palabra del autor; si 0 hits, barrer hacia la
        # izquierda palabra a palabra ("panza de burro" + lopez -> + abreu).
        for word in reversed(words):
            raw = await self.client.fetch_book(title, word, url, port, base)
            if self.number_of_hits(raw) > 0:
                return raw
            last_raw = raw
        return last_raw

    @staticmethod
    def normalize_MARC(title) -> str:
        article_pattern = r'^(el |la |los |las |un |una |unos |unas |els |les |the |a |an |le |un |une |des |l[\'’])'
        
        title_without_article = re.sub(article_pattern, '', title, flags=re.IGNORECASE)
        
        return title_without_article.strip()

    @staticmethod
    def number_of_hits(raw: str) -> int:
        match = re.search(r"Number of hits: (\d+)", raw or "")
        return int(match.group(1)) if match else 0

    async def search_book_brief(self, title: str, author: str, url: str, port: int, base: str) -> str:
        return await self.client.fetch_book_brief(
            self.normalize_MARC(title), author, url, port, base
        )

    async def search_book_author(self, author: str, url: str, port: int, base: str) -> str:
        return await self.client.fetch_book_author(
            self.normalize_MARC(author), url, port, base
        )

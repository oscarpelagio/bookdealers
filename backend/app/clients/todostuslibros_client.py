import httpx
import re
import urllib.parse
from decimal import Decimal, InvalidOperation
from bs4 import BeautifulSoup

from .availability_base_client import AvailabilityBaseClient
from app.schemas import FetchRequest


class TodostuslibrosClient(AvailabilityBaseClient):
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
        )
        self.xsrf_token: str | None = None
        self.last_referer: str | None = None
        self.last_price: Decimal | None = None

    async def fetch_availability(self, request: FetchRequest):
        headers = {"X-Requested-With": "XMLHttpRequest"}
        if self.xsrf_token:
            headers["X-XSRF-TOKEN"] = self.xsrf_token
        if self.last_referer:
            headers["Referer"] = self.last_referer

        response = await self.client.post(request.url, data=request.params, headers=headers)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return response.text

    async def fetch_books(self, request: FetchRequest):
        search_response = await self.client.get(request.url, params=request.params)
        search_response.raise_for_status()

        token = search_response.cookies.get("XSRF-TOKEN")
        if token:
            self.xsrf_token = urllib.parse.unquote(token)
        self.last_referer = str(search_response.url)

        isbn = self._extract_isbn_from_search(search_response.text)
        fallback_isbn = str(request.params.get("isbn") or "").strip()
        if not isbn:
            isbn = fallback_isbn

        self.last_price = self._extract_price_from_search(search_response.text, isbn)

        catalog_url = str(request.params.get("catalog_url") or "").strip()
        if not isbn or not catalog_url:
            return []

        availability_request = FetchRequest(url=catalog_url, params={"isbn": isbn})
        return await self.fetch_availability(availability_request)

    async def fetch_search(self, request: FetchRequest) -> str:
        response = await self.client.get(request.url, params=request.params)
        response.raise_for_status()
        token = response.cookies.get("XSRF-TOKEN")
        if token:
            self.xsrf_token = urllib.parse.unquote(token)
        self.last_referer = str(response.url)
        return response.text

    def _extract_isbn_from_search(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        candidates: list[str] = []
        for node in soup.select("a[href]"):
            href = (node.get("href") or "").split("#", 1)[0].split("?", 1)[0]
            href = href.rstrip("/")
            match = re.search(r"_(\d{3}-\d{2}-[\d-]+)$", href)
            if match:
                candidates.append(match.group(1))

        cleaned: list[tuple[str, str]] = []
        for value in candidates:
            digits = re.sub(r"[^0-9Xx]", "", value or "")
            if len(digits) in (10, 13):
                cleaned.append((value.strip(), digits))

        for original, digits in cleaned:
            if len(digits) == 13:
                return original

        return cleaned[0][0] if cleaned else ""

    def _extract_price_from_search(self, html: str, isbn: str) -> Decimal | None:
        """Extrae el precio del libro desde el HTML de búsqueda.

        El precio aparece en el atributo `data-gtm-precio` del `<li>` que
        corresponde al libro (identificado por `id="book_{isbn}"`).
        """
        if not isbn:
            return None
        soup = BeautifulSoup(html, "html.parser")
        normalized_isbn = re.sub(r"[^0-9Xx]", "", isbn)
        candidates = soup.select("li[data-gtm-precio]")
        for node in candidates:
            node_isbn = re.sub(r"[^0-9Xx]", "", node.get("data-gtm-isbn") or "")
            node_id = re.sub(r"[^0-9Xx]", "", node.get("id") or "")
            if node_isbn and node_isbn == normalized_isbn:
                return self._to_decimal(node.get("data-gtm-precio"))
            if node_id and node_id == normalized_isbn:
                return self._to_decimal(node.get("data-gtm-precio"))
        return None

    def _to_decimal(self, raw: str | None) -> Decimal | None:
        if not raw:
            return None
        cleaned = raw.strip().replace(",", ".").replace("€", "").strip()
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

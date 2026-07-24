"""Adapter for Todostuslibros availability results."""

import json
import re
from bs4 import BeautifulSoup

from app.models import Book, Catalog
from app.schemas import FetchRequest, AvailabilityBase
from app.enums import AvailabilityStatusEnum, EstablishmentTypeEnum
from app.adapters.availability_base_adapter import AvailabilityBaseAdapter


class TodostuslibrosAdapter(AvailabilityBaseAdapter):
    SEARCH_URL = "https://www.todostuslibros.com/busquedas"

    def build_search_query(self, book: Book) -> FetchRequest:
        query_parts = [book.title.strip(), book.author.strip()]
        query = " ".join(part for part in query_parts if part)
        return FetchRequest(url=self.SEARCH_URL, params={"keyword": query})

    def build_search(self, book: Book, catalog: Catalog) -> FetchRequest:
        query_parts = [book.title.strip(), book.author.strip()]
        query = " ".join(part for part in query_parts if part)
        return FetchRequest(
            url=self.SEARCH_URL,
            params={
                "keyword": query,
                "isbn": (book.isbn or "").strip(),
                "catalog_url": catalog.url,
            },
        )

    def build_availability_request(self, isbn: str, catalog: Catalog) -> FetchRequest:
        params = {"isbn": isbn.strip()}
        return FetchRequest(url=catalog.url, params=params)

    def extract_isbn_from_search(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        candidates: list[str] = []
        for node in soup.select("a[href]"):
            href = (node.get("href") or "").split("#", 1)[0].split("?", 1)[0]
            href = href.rstrip("/")
            match = re.search(r"_(\d{3}-\d{2}-[\d-]+)$", href)
            if match:
                candidates.append(match.group(1))
        return self._select_isbn(candidates)

    def response_adapter(self, book: Book, catalog: Catalog, response) -> list[AvailabilityBase]:
        entries = self._extract_entries(response)
        availability: list[AvailabilityBase] = []
        for entry in entries:
            name = (entry.get("name") or "").strip()
            status_text = (entry.get("status") or "").strip()
            availability_code = (entry.get("availability_code") or "").strip()
            quantity = entry.get("quantity")
            link = (entry.get("link") or "").strip()
            address_fields = self._extract_address_fields(entry)
            if not name:
                continue
            availability.append(
                AvailabilityBase(
                    establishment_type=EstablishmentTypeEnum.BOOK_SHOP,
                    establishment_name=name,
                    establishment_street=address_fields["street"],
                    establishment_postal_code=address_fields["postal_code"],
                    establishment_city=address_fields["city"],
                    establishment_province=address_fields["province"],
                    catalog_id=catalog.id,
                    book_id=book.id,
                    book_language=book.language or "",
                    book_status=self._map_status(status_text, availability_code, quantity),
                    queue=None,
                    link=link,
                )
            )
        return availability

    def _extract_entries(self, response) -> list[dict]:
        if isinstance(response, list):
            return self._extract_from_json(response)
        if isinstance(response, dict):
            return self._extract_from_json(response)
        if isinstance(response, str):
            json_entries = self._try_parse_json(response)
            if json_entries:
                return json_entries
        return []

    def _try_parse_json(self, response: str) -> list[dict]:
        try:
            data = json.loads(response)
        except (TypeError, ValueError):
            return []
        return self._extract_from_json(data)

    def _extract_from_json(self, data) -> list[dict]:
        if isinstance(data, list):
            items = data
        else:
            items = data.get("tiendas") or data.get("stores") or data.get("availability") or []
        entries: list[dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            entries.append(
                {
                    "name": item.get("nombre") or item.get("name"),
                    "status": item.get("estado") or item.get("status") or "",
                    "availability_code": item.get("tipo_disponibilidad") or "",
                    "quantity": item.get("cantidad"),
                    "link": item.get("web_libros") or item.get("url") or item.get("link"),
                    "address": item.get("direccion") or item.get("address") or item.get("street") or item.get("calle"),
                    "postal_code": item.get("cp") or item.get("codigo_postal") or item.get("postal_code") or item.get("zip"),
                    "city": item.get("localidad") or item.get("municipio") or item.get("city") or item.get("town"),
                    "province": item.get("provincia") or item.get("province") or item.get("state"),
                }
            )
        return entries

    def _map_status(
        self, status: str, availability_code: str, quantity
    ) -> AvailabilityStatusEnum:
        normalized = status.lower()
        if "disponible hoy" in normalized:
            return AvailabilityStatusEnum.AVAILABLE
        if "on demand" in normalized:
            return AvailabilityStatusEnum.ON_DEMAND
        if "disponible en 2-3 dias" in normalized:
            return AvailabilityStatusEnum.AVAILABLE_IN_2_3_DAYS
        if availability_code == "0":
            return AvailabilityStatusEnum.AVAILABLE
        if availability_code == "1":
            return AvailabilityStatusEnum.AVAILABLE_IN_2_3_DAYS
        if isinstance(quantity, int) and quantity > 0:
            return AvailabilityStatusEnum.AVAILABLE
        return AvailabilityStatusEnum.UNKNOWN

    def _select_isbn(self, candidates: list[str]) -> str:
        cleaned: list[tuple[str, str]] = []
        for value in candidates:
            digits = re.sub(r"[^0-9Xx]", "", value or "")
            if len(digits) in (10, 13):
                cleaned.append((value.strip(), digits))
        for original, digits in cleaned:
            if len(digits) == 13:
                return original
        return cleaned[0][0] if cleaned else ""

    def _extract_address_fields(self, entry: dict) -> dict[str, str | None]:
        raw_address = (entry.get("address") or "").strip()
        street = raw_address or None
        postal_code = (entry.get("postal_code") or "").strip() or None
        city = (entry.get("city") or "").strip() or None
        province = (entry.get("province") or "").strip() or None

        if raw_address and (postal_code is None or city is None or province is None):
            parsed = self._parse_compound_address(raw_address)
            street = parsed["street"] or street
            postal_code = postal_code or parsed["postal_code"]
            city = city or parsed["city"]
            province = province or parsed["province"]

        return {
            "street": street,
            "postal_code": postal_code,
            "city": city,
            "province": province,
        }

    def _parse_compound_address(self, address: str) -> dict[str, str | None]:
        cleaned = address.strip().strip("()")
        street = None
        tail = cleaned
        if " - " in cleaned:
            street, tail = cleaned.split(" - ", 1)
            street = street.strip() or None

        parts = [part.strip() for part in tail.split(",") if part.strip()]

        if street is None and len(parts) >= 2:
            street = ", ".join(parts[:2]).strip() or None
            parts = parts[2:]

        postal_code = None
        city = None
        province = None

        for index, part in enumerate(parts):
            match = re.search(r"\b\d{5}\b", part)
            if match and postal_code is None:
                postal_code = match.group(0)
                if index + 1 < len(parts):
                    city = parts[index + 1].strip() or None
                elif index > 0:
                    city = parts[index - 1].strip() or None
                break

        if city is None and parts:
            first = parts[0].strip()
            if not re.search(r"\b\d{5}\b", first):
                city = first or None

        if parts:
            province = parts[-1].strip() or None

        return {
            "street": street,
            "postal_code": postal_code,
            "city": city,
            "province": province,
        }

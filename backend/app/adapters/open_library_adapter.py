"""Adapter for Open Library search results."""

from __future__ import annotations

from datetime import date
import re

from app.schemas import BookBase
from app.utils import NormalizationUtils
from app.adapters.search_base_adapter import SearchBaseAdapter


class OpenLibraryAdapter(SearchBaseAdapter):
    COVER_URL_TEMPLATE = "https://covers.openlibrary.org/b/id/{cover_id}-{size}.jpg"

    def build_search(
        self, title: str | None, author: str | None, max_results: int = 10
    ) -> dict:
        params: dict[str, str | int] = {
            "limit": max(1, min(max_results, 50)),
        }
        if title:
            params["title"] = title
        if author:
            params["author"] = author
        if not title and not author:
            params["q"] = ""
        return params

    def response_adapter(self, results: dict) -> list[BookBase]:
        docs = results.get("docs", []) if isinstance(results, dict) else []
        return [self._parse_doc(doc) for doc in docs if isinstance(doc, dict)]

    def _parse_doc(self, doc: dict) -> BookBase:
        title = doc.get("title") or "Unknown"
        authors = NormalizationUtils.normalize_list(doc.get("author_name") or ["Unknown"])
        publisher = self._first_string(doc.get("publisher"))
        publisher_date = self._parse_year(doc.get("first_publish_year"))
        isbn = self._extract_isbn(doc.get("isbn") or [])
        page_count = doc.get("number_of_pages_median") or 0
        categories = NormalizationUtils.normalize_list(doc.get("subject"))
        language = self._normalize_language(doc.get("language"))
        preview_link = self._build_preview_link(doc.get("key"))

        cover_id = doc.get("cover_i")
        small_thumbnail = None
        thumbnail = None
        if cover_id:
            cover_id = str(cover_id)
            small_thumbnail = self.COVER_URL_TEMPLATE.format(cover_id=cover_id, size="S")
            thumbnail = self.COVER_URL_TEMPLATE.format(cover_id=cover_id, size="L")

        return BookBase(
            title=title,
            author=authors,
            isbn=isbn,
            publisher=publisher,
            publisher_date=publisher_date,
            description=None,
            page_count=page_count,
            print_type="BOOK",
            categories=categories,
            maturity_rating=None,
            language=language,
            preview_link=preview_link,
            small_thumbnail=small_thumbnail,
            thumbnail=thumbnail,
            normal_title=NormalizationUtils.normalize_text(title),
            normal_author=NormalizationUtils.normalize_text(authors),
        )

    def _build_preview_link(self, key: str | None) -> str | None:
        if not key:
            return None
        return f"https://openlibrary.org{key}"

    def _normalize_language(self, value) -> str:
        if isinstance(value, list) and value:
            return str(value[0])
        if isinstance(value, str) and value:
            return value
        return "und"

    def _parse_year(self, year_value) -> date | None:
        try:
            year = int(year_value)
        except (TypeError, ValueError):
            return None
        if year <= 0:
            return None
        return date(year, 1, 1)

    def _first_string(self, value) -> str | None:
        if isinstance(value, list) and value:
            for item in value:
                if isinstance(item, str) and item.strip():
                    return item.strip()
            return None
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    def _extract_isbn(self, values: list[str]) -> str | None:
        cleaned: list[tuple[str, str]] = []
        for value in values:
            digits = re.sub(r"[^0-9Xx]", "", value or "")
            if len(digits) in (10, 13):
                cleaned.append((value, digits))
        for _, digits in cleaned:
            if len(digits) == 13:
                return digits
        return cleaned[0][1] if cleaned else None

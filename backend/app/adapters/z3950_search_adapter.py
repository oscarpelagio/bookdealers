"""Adapter for Z39.50 search results."""

import re
from datetime import date

from app.schemas import BookBase
from app.utils import NormalizationUtils
from app.adapters.search_base_adapter import SearchBaseAdapter


class Z3950SearchAdapter(SearchBaseAdapter):

    def build_search(
        self, title: str | None, author: str | None, catalog, max_results: int = 10
    ) -> dict:
        return {
            "title": NormalizationUtils.normalize_text(title) if title else "",
            "author": NormalizationUtils.normalize_text(author) if author else "",
            "url": catalog.url,
            "port": catalog.port,
            "base": catalog.base,
        }

    def response_adapter(self, raw_text: str) -> list[BookBase]:
        if not raw_text or not raw_text.strip():
            return []

        records = self._marc_parser(raw_text)
        books = []
        for record in records:
            book = self._record_to_bookbase(record)
            if book:
                books.append(book)
        return books

    def _marc_parser(self, text: str) -> list[dict]:
        record_sections = text.split("Record type: USmarc")
        results = []

        for section in record_sections:
            if not section.strip():
                continue

            record = {}

            id_match = re.search(r"^001\s+(\S+)", section, re.MULTILINE)
            if id_match:
                record["record_id"] = id_match.group(1).strip()

            bib_match = re.search(r"^035\s+.*?\$a\s*([^$\n]+)", section, re.MULTILINE)
            if bib_match:
                record["bib_id"] = bib_match.group(1).strip()

            f008_match = re.search(r"^008\s+(.+)", section, re.MULTILINE)
            if f008_match:
                f008 = f008_match.group(1)
                if len(f008) >= 38:
                    record["language"] = f008[35:38].strip()

            isbn_match = re.search(r"^020\s+.*?\$a\s*([\dX-]+)", section, re.MULTILINE)
            if isbn_match:
                record["isbn"] = isbn_match.group(1).strip()

            author_match = re.search(r"^100\s+.*?\$a\s*([^$\n]+)", section, re.MULTILINE)
            if author_match:
                author_raw = author_match.group(1).strip().rstrip(".,;: ")
                record["author_biblioteca"] = author_raw
                record["author"] = NormalizationUtils.author_name_first(author_raw)

            orig_title_match = re.search(r"^240\s+.*?\$a\s*([^$\n.]+)", section, re.MULTILINE)
            if orig_title_match:
                record["original_title"] = orig_title_match.group(1).strip().rstrip(" /:")

            title_match = re.search(r"^245\s+.*?\$a\s*([^$\n/]+)", section, re.MULTILINE)
            if title_match:
                record["title"] = title_match.group(1).strip().rstrip(" /:")

            pub_match = re.search(r"^(?:260|264)\s+.*?\$b\s*([^$\n]+)", section, re.MULTILINE)
            if pub_match:
                record["publisher"] = pub_match.group(1).strip().rstrip("., ")

            date_match = re.search(r"^(?:260|264)\s+.*?\$c\s*([^$\n]+)", section, re.MULTILINE)
            if date_match:
                date_text = date_match.group(1).strip().rstrip(".")
                year_match = re.search(r"\b(\d{4})\b", date_text)
                if year_match:
                    try:
                        record["publisher_date"] = date(int(year_match.group(1)), 1, 1)
                    except ValueError:
                        pass

            desc_match = re.search(r"^520\s+.*?\$a\s*([^$\n]+)", section, re.MULTILINE)
            if desc_match:
                record["description"] = desc_match.group(1).strip().rstrip(".")

            pages_match = re.search(r"^300\s+.*?\$a\s*(\d+)", section, re.MULTILINE)
            if pages_match:
                record["page_count"] = int(pages_match.group(1))

            record["holdings_count"] = section.count("Data holdings")

            if record.get("title") or record.get("author"):
                results.append(record)

        return results

    def _record_to_bookbase(self, record: dict) -> BookBase | None:
        title = record.get("title", "Unknown")
        author = record.get("author", "Unknown")
        bib_id = record.get("bib_id")

        small_thumbnail = None
        thumbnail = None
        if bib_id:
            cover_base = f"https://portadesbd.diba.cat/img.php?i={bib_id}"
            if record.get("isbn"):
                cover_base += f"&isbn={record['isbn']}"
            small_thumbnail = f"{cover_base}&m=g"
            thumbnail = cover_base

        return BookBase(
            title=title,
            author=NormalizationUtils.normalize_list([author]),
            author_biblioteca=record.get("author_biblioteca"),
            isbn=record.get("isbn"),
            publisher=record.get("publisher"),
            publisher_date=record.get("publisher_date"),
            description=record.get("description"),
            page_count=record.get("page_count") or 0,
            language=record.get("language", "und"),
            original_title=record.get("original_title"),
            bib_id=bib_id,
            small_thumbnail=small_thumbnail,
            thumbnail=thumbnail,
            holdings_count=record.get("holdings_count") or 0,
            normal_title=NormalizationUtils.normalize_text(title),
            normal_author=NormalizationUtils.normalize_text(author),
            normal_original_title=NormalizationUtils.normalize_text(record["original_title"]) if record.get("original_title") else NormalizationUtils.normalize_text(title),
            print_type="BOOK",
        )

from datetime import date    

from app.schemas import BookBase
from app.utils import NormalizationUtils


class GoogleBooksAdapter:

    def build_search(self, title: str, author: str) -> str:
        query_parts = []
        if title:
            t_clean = " ".join(title.split())  # normaliza espacios
            query_parts.append(f"intitle:{t_clean}")
        if author:
            a_clean = " ".join(author.split())  # normaliza espacios
            query_parts.append(f"inauthor:{a_clean}")
        return " ".join(query_parts)


    # def build_search(self, title: str, author: str) -> str:
    #     query_parts = []
    #     if title:
    #         t_clean = title.strip().replace(" ", "+")
    #         query_parts.append(f"intitle:{t_clean}")
    #     if author:
    #         a_clean = author.strip().replace(" ", "+")
    #         query_parts.append(f"inauthor:{a_clean}")
    #     search = "+".join(query_parts)
    #     return search

    def parse_books(self, results: dict) -> list[BookBase]:
        items = results.get("items", [])
        books = [self._parse_book(item) for item in items]        
        return books
    
    def _parse_book(self, item: dict) -> BookBase:
        """
        Converteix el JSON de Google en el model net amb validació.
        """
        google_id = item.get("id", {})
        volume = item.get("volumeInfo", {})

        title=volume.get("title", "Desconegut")
        authors = NormalizationUtils.normalize_list(volume.get("authors", ["Desconegut"]))

        thumbnail = None
        small_thumbnail=self._safe_get_nested(volume, ["imageLinks", "smallThumbnail"])
        if small_thumbnail:
            thumbnail = NormalizationUtils.thumbnail_resize(google_id)

        return BookBase(
            title=title,
            author=authors,
            isbn=self._extract_isbn(volume.get("industryIdentifiers", [])),
            publisher=volume.get("publisher"),
            publisher_date=self._parse_date(volume.get("publishedDate")),
            description=self._safe_get_string(volume, "description"),
            page_count=volume.get("pageCount") or 0,
            print_type=self._safe_get_string(volume, "printType", "BOOK"),
            categories=NormalizationUtils.normalize_list(volume.get("categories")),
            maturity_rating=self._safe_get_string(volume, "maturityRating"),
            language=self._safe_get_string(volume, "language", "und"),
            preview_link=self._safe_get_string(volume, "previewLink"),
            small_thumbnail=small_thumbnail,
            thumbnail=thumbnail,
            normal_title=NormalizationUtils.normalize_text(title),
            normal_author=NormalizationUtils.normalize_text(authors)
        )

    def _extract_isbn(self, identifiers: list[dict]) -> str:
        """Extreu l'ISBN amb prioritat a ISBN_13."""
        isbn_13 = None
        isbn_10 = None
        
        for identifier in identifiers:
            if identifier.get("type") == "ISBN_13":
                isbn_13 = identifier.get("identifier")
            elif identifier.get("type") == "ISBN_10":
                isbn_10 = identifier.get("identifier")
        
        return isbn_13 or isbn_10 or "Sense ISBN"

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parseja dates en diferents formats (YYYY, YYYY-MM, YYYY-MM-DD)."""
        if not date_str:
            return None
            
        try:
            if len(date_str) == 4:  # YYYY
                return date(int(date_str), 1, 1)
            elif len(date_str) == 7:  # YYYY-MM
                parts = date_str.split("-")
                return date(int(parts[0]), int(parts[1]), 1)
            else:  # YYYY-MM-DD
                return date.fromisoformat(date_str)
        except (ValueError, IndexError):
            return None

    def _safe_get_string(self, data: dict, key: str, default: str = "") -> str:
        """Obté un valor string de forma segura."""
        value = data.get(key)
        return str(value) if value is not None else default

    def _safe_get_nested(self, data: dict, keys: list[str]) -> str | None:
        """Obté un valor de diccionaris niats de forma segura."""
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
            if current is None:
                return None
        return current

"""Adapter for eBiblio availability results."""

import re
import json
from bs4 import BeautifulSoup

from app.models import Book, Catalog
from app.utils import NormalizationUtils
from app.schemas import FetchRequest, AvailabilityBase
from app.enums import AvailabilityStatusEnum
from app.adapters.availability_base_adapter import AvailabilityBaseAdapter


class eBiblioAdapter(AvailabilityBaseAdapter):
            
    def build_search(self, book: Book, catalog: Catalog) -> FetchRequest:
        search = f"{book.normal_title.strip()} {book.normal_author.strip()}".strip()
        params = {
            "idioma": "",  
            "callback": "json", 
            "searchArg": search,
            "searchIndex": "X",
            "searchOffset": "0",
            "searchDirect": "1"
        }
        return FetchRequest(url=catalog.url, params=params)
    
    def response_adapter(self, book: Book, catalog: Catalog, response: str) -> list[AvailabilityBase]:
        response_books = self._list_parser(response)
        availability = []
        for response_book in response_books:
            title = NormalizationUtils.normalize_text(response_book.get("title", ""))
            author = NormalizationUtils.normalize_text(response_book.get("author", ""))
            
            if book.normal_title == title and book.normal_author == author:
                availability_data = {
                    "establishment_type": "ebiblio",
                    "establishment_name": "ebiblio", 
                    "catalog_id": catalog.id,
                    "book_id": book.id,
                    "book_language": "vo",
                    "book_status": AvailabilityStatusEnum.AVAILABLE,
                    # "status_exta": None,
                    "link": response_book.get("link", "")
                }
                availability.append(AvailabilityBase(**availability_data))
        return availability

    def _list_parser(self, response: str) -> list[dict]:
        # Extract the quoted payload to build valid JSON.
        # Capture ("...") instead of the inner content.
        match = re.search(r'\((".+?")\)\s*$', response, re.DOTALL)
        if not match:
            return []
        
        json_str = match.group(1)
        
        # Unescape via json.loads() to decode escape sequences.
        html = json.loads(json_str) 
        
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for li in soup.find_all("li", class_="ebiblio-li"):
            title  = li.find("font", class_="ebiblio-info-title")
            author = li.find("font", class_="ebiblio-info-author")
            link   = li.find("a", class_="ebiblio-link")
            if title and author and link:
                results.append({
                    "title":  title.text.strip(),
                    "author": author.text.strip(),
                    "link":   link["href"]
                })
        return results

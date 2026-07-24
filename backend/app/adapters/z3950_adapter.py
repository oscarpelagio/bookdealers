"""Adapter for Z39.50 availability results."""

import re

from app.models import Book, Catalog
from app.schemas import AvailabilityBase, FetchRequest
from app.enums import AvailabilityStatusEnum
from app.core.config import settings
from app.adapters.availability_base_adapter import AvailabilityBaseAdapter


class Z3950Adapter(AvailabilityBaseAdapter):

    def build_search(self, book: Book, catalog: Catalog) -> FetchRequest :
        params = {
        "title": book.normal_title,
        "author": book.normal_author.split()[-1],
        "url": catalog.url,
        "port": catalog.port,
        "base": catalog.base
        }
        return FetchRequest(url=settings.z3950_service_url, params=params)

    
    def response_adapter(self, book: Book, catalog: Catalog, response: dict) -> list[AvailabilityBase]:
        # Extract raw data using the private parser.
        
        if isinstance(response, dict):
            text_content = response.get("response", "")
        else:
            text_content = response

        raw_records = self._marc_parser(text_content)
                
        seen_libraries = {}
        
        for record in raw_records:
            
            language = record.get("language", "unknown")
            record_id = record.get("record_id", "unknown")
            for item in record.get("holdings", []):
                library_name = item.get("location")
                raw_status = item.get("status_raw")
                
                if library_name and raw_status:
                    library_key = (library_name, language, record_id)
                    # Prefer the "available" status when duplicates exist
                    if library_key not in seen_libraries or raw_status.lower() == 'available':
                        seen_libraries[library_key] = self._map_availability_status(raw_status)

        availability = []
        for (library_name, lang, record_id), status in seen_libraries.items():
            availability_data = {
                "establishment_type": "library",
            "establishment_name": library_name,
                "catalog_id": catalog.id,
                "book_id": book.id,
                "book_language": lang,
                "book_status": status[0],
                "queue": status[1],
                "link": catalog.link.replace("###", record_id)
            }
            availability.append(AvailabilityBase(**availability_data))
        
        # Sort by establishment name and language.
        return sorted(availability, key=lambda x: (x.establishment_name, x.book_language))

    def _marc_parser(self, response_text: str) -> list[dict]:
        """Private parser to unpack plain USmarc and holdings text."""
        record_sections = response_text.split('Record type: USmarc')
        results = []

        for record_section in record_sections:
            if not record_section.strip():
                continue
                
            # Extract language (field 907 $f).
            lang_match = re.search(r'^907\s+.*\$f\s*([a-zA-Z]+)', record_section, re.MULTILINE)
            language = lang_match.group(1).strip() if lang_match else "unknown"

            id_match = re.search(r'907\s+.*\$a\s*\.([a-zA-Z0-9]+)', record_section)
            record_id = id_match.group(1)[:-1] if id_match else None

            print(f'!!!!!!!!! RECORD : {record_id}')
            # Extract holdings (copy blocks).
            holdings_blocks = record_section.split('Data holdings')
            holdings = []
            
            for holding_block in holdings_blocks[1:]:
                loc_match = re.search(r'localLocation:\s*([^\n]+)', holding_block)
                status_match = re.search(r'publicNote:\s*([^\n]+)', holding_block)
                
                if loc_match and status_match:
                    # Clean the location (e.g., "BC - General" -> "BC").
                    clean_location = loc_match.group(1).split('-')[0].strip()
                    if clean_location:
                        holdings.append({
                            "location": clean_location,
                            "status_raw": status_match.group(1).strip()
                        })
            
            if holdings:
                results.append({
                    "language": language,
                    "holdings": holdings,
                    "record_id": record_id
                })
                
        return results

    def _map_availability_status(self, status_str: str) -> tuple[AvailabilityStatusEnum, int | None]:
        """Map catalog status strings to application enums."""
        status_lower = status_str.lower()
        
        # Catalog status values can be in Spanish; keep raw tokens for matching.
        if any(word in status_lower for word in ["disponible", "available", "en estante"]):
            return AvailabilityStatusEnum.AVAILABLE, None

        if any(word in status_lower for word in ["in transit", "due", "on hold"]):
            if "+" in status_lower:
                status_lower_end = status_lower.split("+")[1]
                queue = status_lower_end.split(" ")[0]
                return AvailabilityStatusEnum.BORROW, queue
            return AvailabilityStatusEnum.BORROW, 0

        if any(word in status_lower for word in ["g-not sent"]):
            return AvailabilityStatusEnum.LOST, None
        
        if any(word in status_lower for word in ["lib use only"]):
            return AvailabilityStatusEnum.LIB_USE_ONLY, None

        print(f'    %%%%% UNKNOWN {status_lower}')
        return AvailabilityStatusEnum.UNKNOWN, None

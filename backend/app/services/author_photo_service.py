"""Servicio de fotos de autor.

Cadena de búsqueda (solo se consulta la siguiente fuente si la anterior no
encuentra nada):

1. Wikipedia (pageimages, es → ca → en) — rápido y sin scraping.
2. Wikidata (P18) si la página existe pero no tiene imagen destacada.
3. Google Images via el microservicio photo-scraper (Playwright headless).

El resultado se cachea en `author_photos` (también los "missing", para no
repetir el scraping de Google).
"""

import urllib.parse
from datetime import datetime, timedelta

import httpx

from app.crud import AuthorPhotoRepository
from app.clients import GooglePhotoClient
from app.utils import NormalizationUtils

LANGUAGES = ["es", "ca", "en"]
WIKIPEDIA_TIMEOUT = 10.0
WIKIDATA_TIMEOUT = 10.0
# Los "missing" se re-intentan al cabo de 7 días (Google bloquea a ratos y no
# debemos condenar a un autor para siempre por un mal día del scraper).
MISSING_RETRY_DAYS = 7

# Wikimedia exige un User-Agent descriptivo; httpx por defecto (python-httpx)
# responde 403 Forbidden.
HTTP_HEADERS = {
    "User-Agent": "BookDealers/1.0 (https://github.com/bookdealers/app; admin@bookdealers.app)",
    "Accept": "application/json",
}


class AuthorPhotoService:

    def __init__(
        self,
        repo: AuthorPhotoRepository,
        client: GooglePhotoClient,
    ) -> None:
        self.repo = repo
        self.client = client

    async def get_photo(self, author: str) -> dict:
        author = (author or "").strip()
        if not author:
            return {"author": author, "photo_url": None, "source": None, "status": "missing"}

        author_key = NormalizationUtils.normalize_text(author)

        cached = await self.repo.get_photo(author_key)
        if cached is not None:
            stale_missing = (
                cached.status == "missing"
                and cached.fetched_at is not None
                and cached.fetched_at
                < datetime.utcnow() - timedelta(days=MISSING_RETRY_DAYS)
            )
            if not stale_missing:
                return {
                    "author": author,
                    "photo_url": cached.photo_url,
                    "source": cached.source,
                    "status": cached.status,
                }

        photo_url, source = await self._search_chain(author)
        status = "found" if photo_url else "missing"
        await self.repo.set_photo(
            author_key, photo_url, source if photo_url else None, status
        )
        return {
            "author": author,
            "photo_url": photo_url,
            "source": source,
            "status": status,
        }

    async def _search_chain(self, author: str) -> tuple[str | None, str | None]:
        # 1) Wikipedia pageimages
        try:
            photo, qid = await self._wikipedia_photo(author)
            if photo:
                return photo, "wikipedia"
        except Exception as exc:
            print(f"[author-photo] error wikipedia para '{author}': {exc!r}")
            photo, qid = None, None

        # 2) Wikidata P18
        if qid:
            try:
                photo = await self._wikidata_photo(qid)
                if photo:
                    return photo, "wikidata"
            except Exception as exc:
                print(f"[author-photo] error wikidata para '{author}' ({qid}): {exc!r}")

        # 3) Google Images (photo-scraper)
        try:
            result = await self.client.fetch_photo(author)
            image_url = result.get("image_url")
            if image_url:
                return image_url, "google"
        except Exception as exc:
            print(f"[author-photo] error google para '{author}': {exc!r}")

        return None, None

    # ------ Fuentes ------

    async def _wikipedia_photo(self, author: str) -> tuple[str | None, str | None]:
        """Devuelve (url_thumbnail, wikibase_item) para el primer idioma que
        tenga imagen o página."""
        params = {
            "action": "query",
            "prop": "pageimages|pageprops",
            "titles": author,
            "format": "json",
            "pithumbsize": 400,
            "redirects": 1,
        }
        async with httpx.AsyncClient(timeout=WIKIPEDIA_TIMEOUT) as client:
            for lang in LANGUAGES:
                response = await client.get(
                    f"https://{lang}.wikipedia.org/w/api.php",
                    params=params,
                    headers=HTTP_HEADERS,
                )
                response.raise_for_status()
                data = response.json()
                pages = (data.get("query") or {}).get("pages") or {}
                qid = None
                for page in pages.values():
                    if page.get("missing"):
                        continue
                    thumb = (page.get("thumbnail") or {}).get("source")
                    if thumb:
                        return thumb, None
                    if qid is None:
                        qid = (page.get("pageprops") or {}).get("wikibase_item")
                return None, qid
        return None, None

    async def _wikidata_photo(self, qid: str) -> str | None:
        async with httpx.AsyncClient(timeout=WIKIDATA_TIMEOUT) as client:
            response = await client.get(
                f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
                headers=HTTP_HEADERS,
            )
            response.raise_for_status()
            data = response.json()
            entity = (data.get("entities") or {}).get(qid) or {}
            claims = entity.get("claims") or {}
            p18 = claims.get("P18") or []
            if not p18:
                return None
            value = (
                (p18[0].get("mainsnak") or {}).get("datavalue") or {}
            ).get("value")
            if not value:
                return None
            return "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(
                str(value)
            )
"""Adapter per al volcat d'autors de Blackie Books (blackiebooks.org).

S'usa la REST API de WordPress (`/wp-json/wp/v2/autor`), que exposa el
mateix contingut que les pàgines HTML (`/autores/` i `/autor/{slug}/`) però
sense bloqueig per IP i amb estructura neta:
- Llistat: paginat (274 autors, 100 per pàgina).
- Perfil: `title.rendered` (nom), `content.rendered` (bio, el mateix bloc
  `div.wp-content` de la pàgina HTML) i `_links.wp:featuredmedia` → foto.
"""

import html as _html
import re
from dataclasses import dataclass


@dataclass
class BlackieProfile:
    name: str
    description: str | None = None
    image_url: str | None = None
    media_id: int | None = None


_TAG_RE = re.compile(r"<[^>]+>")


def _clean_text(raw: str) -> str | None:
    if not raw:
        return None
    text = _TAG_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip() or None


def parse_authors_index(items: list[dict]) -> list[str]:
    """Devuelve los slugs del listado de la REST API (sin duplicados)."""
    slugs: list[str] = []
    seen: set[str] = set()
    for item in items:
        slug = (item.get("slug") or "").strip()
        if slug and slug not in seen:
            seen.add(slug)
            slugs.append(slug)
    return slugs


def parse_profile(item: dict) -> BlackieProfile:
    """Parseo de un ítem de autor de la REST API (name/bio/media)."""
    name = _clean_text(item.get("title", {}).get("rendered") or "")
    description = _clean_text(item.get("content", {}).get("rendered") or "")
    media_id = None
    media = (item.get("_links", {}).get("wp:featuredmedia") or [])
    if media:
        href = media[0].get("href") or ""
        m = re.search(r"/media/(\d+)$", href)
        if m:
            media_id = int(m.group(1))
    return BlackieProfile(
        name=name or "",
        description=description,
        media_id=media_id,
    )


def parse_media_url(media: dict) -> str | None:
    """Devuelve la URL directa de la foto desde el ítem de media."""
    url = media.get("source_url")
    return url.strip() if url else None
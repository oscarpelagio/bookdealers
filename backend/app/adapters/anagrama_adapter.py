"""Adapter para el volcado de autores de Anagrama (anagrama-ed.es).

Parseo de dos tipos de página:
- `/autores/{letra}`: índice alfabético → slugs de perfil.
- `/autor/{slug}-{id}`: perfil → nombre, bio, enlace a foto y "contenido
  relacionado" (videos/entrevistas/articles) en `extra`.
"""

import html as _html
import re
from dataclasses import dataclass, field


@dataclass
class AnagramaProfile:
    name: str
    description: str | None = None
    image_url: str | None = None
    extra: list[dict] = field(default_factory=list)


_SLUG_RE = re.compile(r'<h2><a href="(/autor/[^"]+)"')
_H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
_OG_TITLE_RE = re.compile(r'<meta property="og:title" content="([^"]*)"')
_PROSE_RE = re.compile(r'<div class="prose[^"]*"[^>]*>', re.I)
_PHOTO_RE = re.compile(
    r"https://cms\.anagrama-ed\.es/uploads/media/autores/[^\"']+?autores_big\.(?:jpe?g|png|webp)"
)
_RELATED_H2_RE = re.compile(r"(?i)contenido relacionado")
_SLIDE_RE = re.compile(r'<div class="swiper-slide">')
_SLIDE_END_RE = re.compile(r"<!--\]-->")
_TYPE_RE = re.compile(r'uppercase">([^<]+)<')
_TITLE_RE = re.compile(r'<h2[^>]*><span>([^<]+)</span></h2>')
_LINK_RE = re.compile(r'href="(/[^"?]+)')
_FECHA_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")
_EXTRACT_RE = re.compile(r'extractolista="([^"]+)"')
_THUMB_RE = re.compile(r"https://cms\.anagrama-ed\.es/uploads/media/[^\"']+")


def parse_letter_index(html: str) -> list[str]:
    """Devuelve los slugs `/autor/...` listados en una página de letra."""
    if not html:
        return []
    return _SLUG_RE.findall(html)


def _extract_prose(html: str, start: int) -> str | None:
    m = _PROSE_RE.search(html, start)
    if not m:
        return None
    open_pos = m.end()
    close = html.find("</div>", html.find("</div>", open_pos) + 1)
    if close == -1:
        return None
    raw = html[open_pos:close]
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip() or None


def _extract_extra(html: str, start: int) -> list[dict]:
    """Extrae todos los ítems de 'contenido relacionado' (tipo VIDEO, etc.)."""
    items: list[dict] = []
    pos = start
    while True:
        slide = _SLIDE_RE.search(html, pos)
        if not slide:
            break
        end = _SLIDE_END_RE.search(html, slide.end())
        if not end:
            break
        block = html[slide.end() : end.start()]
        links = [
            u
            for u in _LINK_RE.findall(block)
            if not u.startswith(("/autor/", "/autores/"))
        ]
        if not links and not _TITLE_RE.search(block):
            pos = end.end()
            continue
        tipo = _TYPE_RE.search(block)
        titulo = _TITLE_RE.search(block)
        fecha = _FECHA_RE.search(block)
        ex = _EXTRACT_RE.search(block)
        thumb = _THUMB_RE.search(block)
        items.append(
            {
                "tipo": (tipo.group(1).strip() if tipo else None),
                "titulo": (titulo.group(1).strip() if titulo else None),
                "url": (links[0].split("?")[0] if links else None),
                "fecha": (fecha.group(1) if fecha else None),
                "descripcion": (
                    re.sub(r"\s+", " ", _html.unescape(ex.group(1))).strip()
                    if ex
                    else None
                ),
                "thumbnail": (thumb.group(0) if thumb else None),
            }
        )
        pos = end.end()
    return items


def parse_profile(html: str) -> AnagramaProfile:
    """Parseo de la página de perfil de un autor."""
    if not html:
        return AnagramaProfile(name="")

    h1 = _H1_RE.search(html)
    name = None
    if h1:
        name = re.sub(r"<[^>]+>", "", h1.group(1)).strip()
    if not name:
        og = _OG_TITLE_RE.search(html)
        name = og.group(1).strip() if og else ""

    photo = _PHOTO_RE.search(html)
    image_url = photo.group(0) if photo else None

    rel = _RELATED_H2_RE.search(html)
    rel_start = rel.start() if rel else len(html)

    description = _extract_prose(html, 0)
    extra = _extract_extra(html, rel_start)

    return AnagramaProfile(
        name=name,
        description=description,
        image_url=image_url,
        extra=extra,
    )

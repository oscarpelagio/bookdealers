"""Adapter para el volcado de Libros del Asteroide (librosdelasteroide.com).

- Índice (`/autores`): tarjetas con slug + nombre (`h4`) para resolver
  autor→URL de perfil sin buscador.
- Perfil (`/autor/{slug}`): nombre (`h1`), bio (`p`) y foto (`img`), todo en
  la misma página.
"""

import html as _html
import re
from dataclasses import dataclass


@dataclass
class AsteroideIndexEntry:
    slug: str
    name: str


@dataclass
class AsteroideProfile:
    name: str
    description: str | None = None
    image_url: str | None = None


_TAG_RE = re.compile(r"<[^>]+>")
_SLUG_RE = re.compile(r'href="(https://librosdelasteroide\.com/autor/[^"]+)"')
_INDEX_NAME_RE = re.compile(
    r'<h4[^>]*class="font-17 text-dark"[^>]*>\s*([^<]+?)\s*</h4>', re.S
)
_INDEX_QT_RE = re.compile(r"<h4[^>]*>\s*([^<]+?)\s*</h4>", re.S)
_H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
_OG_DESC_RE = re.compile(
    r'<meta name="description" content="([^"]*)"'
)
_PROSE_RE = re.compile(r"<p class=\"mb-0\">(?P<body>.*?)</p>", re.S)
_IMG_RE = re.compile(
    r'<img[^>]*class="img-fluid mb-8"[^>]*src="([^"]+)"', re.I
)


def clean_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = _TAG_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip() or None


def parse_authors_index(html: str) -> list[AsteroideIndexEntry]:
    """Devuelve las entradas (slug + nombre) del listado `/autores`.

    Los bloques van precedidos por un `<a class="cbp-caption"
    href=".../autor/{slug}">...<h4 class="font-17 text-dark">{nombre}</h4>`."""
    entries: list[AsteroideIndexEntry] = []
    if not html:
        return entries
    # Las tarjetas de autor empiezan por el enlace del slug.
    for slug_match in _SLUG_RE.finditer(html):
        block = html[slug_match.start() : slug_match.end() + 600]
        name = None
        nm = _INDEX_NAME_RE.search(block) or _INDEX_QT_RE.search(block)
        if nm:
            name = clean_text(nm.group(1))
        slug = slug_match.group(1).removeprefix("https://librosdelasteroide.com/autor/").rstrip("/")
        if slug and name and name != "Autores":
            entries.append(AsteroideIndexEntry(slug=slug, name=name))
    return entries


def parse_profile(html: str) -> AsteroideProfile:
    """Parseo de la página `/autor/{slug}`: nombre, bio y foto."""
    if not html:
        return AsteroideProfile(name="")

    name = None
    h1 = _H1_RE.search(html)
    if h1:
        name = clean_text(h1.group(1))

    description = None
    prose = _PROSE_RE.search(html)
    if prose:
        description = clean_text(prose.group("body"))

    image_url = None
    img = _IMG_RE.search(html)
    if img:
        image_url = img.group(1)

    return AsteroideProfile(
        name=name or "",
        description=description,
        image_url=image_url,
    )
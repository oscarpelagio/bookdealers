"""Adapter per al volcat d'autors de Penguin Libros (penguinlibros.com).

Cada autor és una categoria de PrestaShop: `/es/{id}-{slug}`. Del perfil
s'extreu nom, bio, foto i "contenido relacionado":
- Booktrailers (pestaña 3): iframes de YouTube → `{tipo: "Vídeo"}`.
- Artículos relacionados (bloc `.simpleblog-posts-column`): `{tipo: "Artículo"}`.
"""

import html as _html
import re
from dataclasses import dataclass, field
from itertools import zip_longest

BASE_URL = "https://www.penguinlibros.com"
ELASTICO_URL = (
    "https://www.penguinlibros.com/es/"
    "?fc=module&module=elastico&controller=elasticosearch"
)


@dataclass
class PenguinAuthor:
    author_id: int
    name: str
    slug: str | None = None


@dataclass
class PenguinIndexEntry:
    """Una entrada de l'índex d'autors (`/es/5-autores?pageno=N`)."""

    author_id: int
    slug: str
    name: str
    thumb: str | None = None


@dataclass
class PenguinProfile:
    name: str
    description: str | None = None
    image_url: str | None = None
    extra: list[dict] = field(default_factory=list)


_H1_RE = re.compile(r'<h1 class="tituloAutorLanding">([^<]+)</h1>')
_INDEX_CARD_RE = re.compile(
    r'<div class="subcategory-image-nuevo[^"]*">\s*<a[^>]*>\s*<img[^>]*src="([^"]+)"[^>]*>.*?'
    r'<a class="subcategory-name-autor"[^>]*href="([^"]+)"[^>]*>\s*([^<]+?)\s*</a>',
    re.S,
)
_INDEX_SLUG_RE = re.compile(r"/es/(\d+)-(.*?)-?$")
NO_PHOTO = "no-foto-autor.png"
_META_DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"')
_BIO_SHORT_RE = re.compile(r'<div class="p_leer_mas[^"]*"[^>]*>(.*?)</div>', re.S)
_BIO_FULL_RE = re.compile(r'<div class="p_leer_menos[^"]*"[^>]*>(.*?)</div>', re.S)
_PHOTO_RE = re.compile(
    r'(?:src|content)=["\']((?:https?://(?:www\.)?penguinlibros\.com)?/es/c/\d+-category_autores/[^"\']+?\.webp)["\']'
)
_YOUTUBE_RE = re.compile(
    r'post-thumbnail\b.*?youtube(?:-nocookie)?\.com/embed/([\w-]+).*?'
    r'post-title\b.*?<a[^>]*>\s*([^<]{1,160}?)\s*</a>',
    re.S,
)
_ARTICLE_URL_RE = re.compile(r'<a class="enlace-post" href="([^"]+)"')
_ARTICLE_THUMB_RE = re.compile(r'<img[^>]*src="([^"]+)"[^>]*class="img-fluid photo"')
_ARTICLE_CAT_RE = re.compile(r'<span class="categoriablog">([^<]+)</span>')
_ARTICLE_TITLE_RE = re.compile(
    r'<div class="post-title">\s*<a[^>]*>\s*([^<]{1,160}?)\s*</a>'
)
_ARTICLE_CONTENT_RE = re.compile(r'<div class="post-content">(.*?)</div>', re.S)
_ARTICLE_ICON_RE = re.compile(r'<div class="icon">.*?<span class="guion">([^<]+)</span>', re.S)


def _clean_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip() or None


def parse_author_index(html: str) -> list[PenguinIndexEntry]:
    """Parseja una pàgina de l'índex d'autors (12 per pàgina)."""
    entries: list[PenguinIndexEntry] = []
    if not html:
        return entries
    for thumb, href, name in _INDEX_CARD_RE.findall(html):
        m = _INDEX_SLUG_RE.search(href)
        if not m:
            continue
        author_id = int(m.group(1))
        slug = (m.group(2) or "").rstrip("-")
        if NO_PHOTO in thumb:
            thumb = None
        else:
            thumb = _abs_url(thumb)
        entries.append(
            PenguinIndexEntry(
                author_id=author_id,
                slug=slug,
                name=_html.unescape(name).strip(),
                thumb=thumb,
            )
        )
    return entries


def parse_author_search(payload) -> list[PenguinAuthor]:
    """Interpreta la resposta JSON del cercador Elastico d'autors."""
    authors: list[PenguinAuthor] = []
    try:
        products = (payload or {}).get("autores", {}).get("products") or []
    except AttributeError:
        return authors
    for item in products:
        if not isinstance(item, dict):
            continue
        author_id = item.get("id")
        name = item.get("name")
        if author_id is None or not name:
            continue
        link = item.get("link") or item.get("url") or ""
        m = re.search(r"/es/(\d+)(?:-([^/?]+?))?(?:[/?]|$)", link) if link else None
        slug = m.group(2) if m else None
        authors.append(PenguinAuthor(author_id=int(author_id), name=name, slug=slug))
    return authors


def parse_profile(html: str) -> PenguinProfile:
    """Parseja la pàgina de perfil d'un autor (`/es/{id}-{slug}`)."""
    if not html:
        return PenguinProfile(name="")

    h1 = _H1_RE.search(html)
    name = h1.group(1).strip() if h1 else ""

    bio_full = _BIO_FULL_RE.search(html)
    bio_short = _BIO_SHORT_RE.search(html)
    if bio_full:
        description = _clean_text(bio_full.group(1))
    elif bio_short:
        description = _clean_text(bio_short.group(1))
    else:
        meta = _META_DESC_RE.search(html)
        description = _clean_text(meta.group(1)) if meta else None

    photo = _PHOTO_RE.search(html)
    if photo:
        url = photo.group(1)
        image_url = url if url.startswith("http") else f"{BASE_URL}{url}"
    else:
        image_url = None

    extra: list[dict] = []
    for match in _YOUTUBE_RE.finditer(html):
        video_id, title = match.group(1), match.group(2).strip()
        extra.append(
            {
                "tipo": "Vídeo",
                "titulo": _html.unescape(title),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "fecha": None,
                "descripcion": None,
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            }
        )
    urls = _ARTICLE_URL_RE.findall(html)
    thumbs = _ARTICLE_THUMB_RE.findall(html)
    cats = _ARTICLE_CAT_RE.findall(html)
    titles = _ARTICLE_TITLE_RE.findall(html)
    contents = _ARTICLE_CONTENT_RE.findall(html)
    icons = _ARTICLE_ICON_RE.findall(html)
    for url, thumb, cat, title, content, icon in zip_longest(
        urls, thumbs, cats, titles, contents, icons
    ):
        extra.append(
            {
                "tipo": "Artículo",
                "titulo": _html.unescape(title).strip() if title else None,
                "url": _abs_url(url) if url else None,
                "fecha": None,
                "descripcion": _clean_text(content) if content else None,
                "thumbnail": _abs_url(thumb) if thumb else None,
                "categoria": _html.unescape(cat).strip() if cat else None,
                "tipo_icono": _html.unescape(icon).strip() if icon else None,
            }
        )

    return PenguinProfile(
        name=name,
        description=description,
        image_url=image_url,
        extra=extra,
    )


def _abs_url(url: str) -> str:
    if url.startswith("http"):
        return url
    if url.startswith("//"):
        return f"https:{url}"
    return f"{BASE_URL}{url}"

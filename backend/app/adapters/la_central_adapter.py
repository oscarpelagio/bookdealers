"""Adapter per al blog de La Central (lacentral.com/blog).

- `parse_listing(html)`: tarjetes del llistat `/blog/tipo/tematicas?pg=N`
  → slug, url, tipus, títol, subtítol, autor, intro (primer paràgraf).
- `parse_article(html, slug)`: article complet (`section#articulo`)
  → títol, subtítol, intro citada, autor, data, cos, portada i llibres.
"""

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

ARTICULO_URL = "https://www.lacentral.com/blog"


@dataclass
class LaCentralCard:
    """Tarjeta del llistat del blog."""

    slug: str
    url: str
    tipo: str | None = None
    titulo: str | None = None
    subtitulo: str | None = None
    autor: str | None = None
    intro: str | None = None


@dataclass
class LaCentralBook:
    """Un llibre de la llista d'un article."""

    titulo: str
    autor: str
    posicion: int


@dataclass
class LaCentralArticle:
    """Article complet del blog."""

    slug: str
    url: str
    tipo: str | None = None
    titulo: str | None = None
    subtitulo: str | None = None
    intro: str | None = None
    autor: str | None = None
    fecha: str | None = None
    cuerpo: str | None = None
    portada_url: str | None = None
    libros: list[LaCentralBook] = field(default_factory=list)


_AUTOR_PREFIX_RE = re.compile(r"^\s*Per\s+", re.I)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.replace("\u200b", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _author_strip(autor: str | None) -> str | None:
    if not autor:
        return None
    return _AUTOR_PREFIX_RE.sub("", autor).strip() or None


def parse_listing(html: str) -> list[LaCentralCard]:
    """Extrau les tarjetes (`div.blog-articulo`) del llistat."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards: list[LaCentralCard] = []
    for card in soup.find_all("div", class_="blog-articulo"):
        link = card.find("a", href=re.compile(r"^/blog/"))
        if not link:
            continue
        href = link["href"]
        slug = href.rsplit("/", 1)[-1].strip()
        if not slug:
            continue

        tipo_el = card.find("p", class_="blog-articulo__tipo")
        titulo_el = card.find("h3", class_="blog-articulo__titulo")
        subtitulo_el = card.find("h4", class_="blog-articulo__subtitulo")
        autor_el = card.find("p", class_="blog-articulo__autor")

        # La intro del llistat és el primer <p> de text pla darrere de l'autor.
        intro = None
        intro_p = card.find("p", class_=None)
        if intro_p:
            intro = _clean(intro_p.get_text(" ", strip=True))

        cards.append(
            LaCentralCard(
                slug=slug,
                url=f"{ARTICULO_URL}/{slug}",
                tipo=_clean(tipo_el.get_text(strip=True)) if tipo_el else None,
                titulo=_clean(titulo_el.get_text(strip=True)) if titulo_el else None,
                subtitulo=_clean(subtitulo_el.get_text(strip=True)) if subtitulo_el else None,
                autor=_author_strip(autor_el.get_text(strip=True)) if autor_el else None,
                intro=intro,
            )
        )
    return cards


def parse_article(html: str, slug: str) -> LaCentralArticle:
    """Extrau un article complet des de `section#articulo`."""
    if not html:
        return LaCentralArticle(slug=slug, url=f"{ARTICULO_URL}/{slug}")

    soup = BeautifulSoup(html, "html.parser")
    sec = soup.find("section", id="articulo") or soup

    tipo_el = sec.find("p", class_="blog-articulo__tipo")
    titulo_el = sec.find("h3", class_="blog-articulo__titulo")

    # Subtítol curt + intro citada: el primer h4 és el curt; els següents
    # (si n'hi ha) van numerats com a intro. Busquem el que parla de cites «...».
    subtitulo = None
    intro = None
    subtitulos = sec.find_all("h4", class_="blog-articulo__subtitulo")
    for i, h4 in enumerate(subtitulos):
        txt = _clean(h4.get_text(strip=True))
        if not txt:
            continue
        if i == 0 and "«" not in txt:
            subtitulo = txt
        elif txt.startswith("«") or txt.startswith("”") or txt.startswith('"'):
            intro = txt
        else:
            subtitulo = subtitulo or txt

    autor_el = sec.find("span", class_="blog-articulo__autor")
    autor = _author_strip(autor_el.get_text(strip=True)) if autor_el else None

    # Data: el <p> on viu l'autor conté autor + data separats.
    fecha = None
    if autor_el:
        p = autor_el.parent
        fecha = _extract_fecha(p.get_text(" ", strip=True)) if p else None

    cuerpo_el = sec.find("div", class_="blog-articulo__contenido")
    cuerpo = (
        re.sub(r"\n{3,}", "\n\n", cuerpo_el.get_text("\n", strip=True)).strip()
        if cuerpo_el
        else None
    )

    portada_url = None
    hero = sec.find(id="articulo__hero")
    if hero:
        img = hero.find("img")
        if img and img.get("src"):
            portada_url = img["src"]

    libros = parse_libros(sec)

    return LaCentralArticle(
        slug=slug,
        url=f"{ARTICULO_URL}/{slug}",
        tipo=_clean(tipo_el.get_text(strip=True)) if tipo_el else None,
        titulo=_clean(titulo_el.get_text(strip=True)) if titulo_el else None,
        subtitulo=subtitulo,
        intro=intro,
        autor=autor,
        fecha=fecha,
        cuerpo=cuerpo,
        portada_url=portada_url,
        libros=libros,
    )


def parse_libros(sec) -> list[LaCentralBook]:
    """Llibres de la llista de l'article (`div.libro` dins de la secció)."""
    libros: list[LaCentralBook] = []
    nodes = sec.find_all("div", class_="libro")
    for pos, node in enumerate(nodes):
        autor_el = node.find("span", class_="libro__autor")
        titulo_el = node.find("a", class_="libro__titulo")
        autor = (
            _author_strip(_clean(autor_el.get_text(strip=True)))
            if autor_el
            else None
        )
        titulo = _clean(titulo_el.get_text(strip=True)) if titulo_el else None
        if not titulo:
            continue
        libros.append(
            LaCentralBook(
                titulo=titulo,
                autor=autor or "",
                posicion=pos,
            )
        )
    return libros


def _extract_fecha(text: str) -> str | None:
    match = re.search(r"\d{1,2}\.\d{1,2}\.\d{4}", text)
    return match.group(0) if match else None
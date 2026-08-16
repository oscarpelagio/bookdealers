"""Adapter para el volcado de autoras de Editorial Tránsito (editorialtransito.es).

La página `/autoras/` trae todo en una sola página: 52 tarjetas
`div.dfd-team-member` con nombre, foto (thumb `-400x400`) y bio. No hay
páginas de perfil individuales que rastrear.
"""

import html as _html
import re
from dataclasses import dataclass


@dataclass
class TransitoProfile:
    name: str
    description: str | None = None
    image_url: str | None = None


_TAG_RE = re.compile(r"<[^>]+>")
_MEMBER_START_RE = re.compile(r'<div class="dfd-team-member[^"]*"[^>]*>')
_SPACER_RE = re.compile(r'<div class="dfd-spacer-module"')
_HEADER_RE = re.compile(
    r'<h5 class="team-member-title[^"]*"[^>]*>\s*<a[^>]*>(?P<name>.*?)</a>',
    re.S | re.I,
)
_BOLD_NAME_RE = re.compile(r"<b>(?P<name>[^<]+)</b>")
_IMAGE_RE = re.compile(r'<img[^>]*class="team-member-photo[^"]*"[^>]*>', re.I)
_DESCRIPTION_RE = re.compile(
    r'<div class="team-member-description[^"]*"[^>]*>(?P<body>.*?)</div>',
    re.S,
)


def clean_text(raw: str) -> str | None:
    if not raw:
        return None
    text = _TAG_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip() or None


def _canonical_name(raw: str | None, fallback: str) -> str:
    """Nombre canónico: el `<b>Nombre</b>` que abre la bio (evita caer en
    mayúsculas). Si no hay `<b>`, usa el h5 en title case."""
    if raw:
        bold = _BOLD_NAME_RE.search(raw)
        if bold:
            name = clean_text(bold.group("name") or "")
            if name:
                return name
    return fallback.title() if fallback else fallback


def parse_card(block: str) -> TransitoProfile | None:
    """Parseo de una tarjeta `div.dfd-team-member` → ítem de autor."""
    header = _HEADER_RE.search(block)
    if not header:
        return None
    name = clean_text(header.group("name") or "")
    if not name:
        return None

    raw_description = None
    desc_match = _DESCRIPTION_RE.search(block)
    if desc_match:
        raw_description = desc_match.group("body")
    description = clean_text(raw_description)

    image_url = None
    img = _IMAGE_RE.search(block)
    if img:
        src = re.search(r'src="([^"]+)"', img.group(0))
        if src:
            # Quita el sufijo de tamaño de WordPress ("...-400x400.jpg")
            # para quedarse con la imagen original.
            image_url = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", src.group(1))

    name = _canonical_name(raw_description, name)
    return TransitoProfile(
        name=name,
        description=description,
        image_url=image_url,
    )


def parse_authors_page(html: str) -> list[TransitoProfile]:
    """Devuelve las autoras listadas en la página `/autoras/`."""
    profiles: list[TransitoProfile] = []
    if not html:
        return profiles
    for match in _MEMBER_START_RE.finditer(html):
        spacer = _SPACER_RE.search(html, match.end())
        block = html[match.end() : spacer.start() if spacer else len(html)]
        profile = parse_card(block)
        if profile:
            profiles.append(profile)
    return profiles
"""Proxy de miniaturas: recorta els marges blancs de les portades de Penguin.

Les portades de penguinlibros.com arriben quadrades (les imatges d'article
són `img-fluid photo`) amb la portada real (vertical o horitzontal) dins i
marges blancs al voltant. Aquest endpoint les descarrega, retalla el borde
blanc amb Pillow (`ImageChops.difference` + umbral) i retorna la imatge ja
retallada en JPEG amb cache a CDN.

Només s'accepten URLs de `*.penguinlibros.com` per evitar SSRF.
"""

import io
import re
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from PIL import Image, ImageChops

router = APIRouter()

_HOST_RE = re.compile(r"(^|\.)penguinlibros\.com$", re.I)
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    return bool(_HOST_RE.search(parsed.hostname))


def _trim_white(image: Image.Image, tolerance: int = 28) -> Image.Image:
    """Retalla els marges (gairebé) blancs de la imatge."""
    rgb = image.convert("RGB")
    bg = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, bg)
    diff = ImageChops.add(diff, diff, 2.0, -tolerance)
    bbox = diff.getbbox()
    if not bbox:
        return image
    left, top, right, bottom = bbox
    if (right - left, bottom - top) == rgb.size:
        return image
    pad = 1
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(rgb.size[0], right + pad)
    bottom = min(rgb.size[1], bottom + pad)
    return rgb.crop((left, top, right, bottom))


@router.get("")
async def get_thumb(url: str = Query(...)):
    """Devuelve la imagen de `url` con los bordes blancos retallados (JPEG)."""
    if not _is_allowed(url):
        raise HTTPException(status_code=400, detail="URL no permitida")

    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={"User-Agent": UA},
        ) as client:
            response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo descargar la imagen: {exc}")

    try:
        image = Image.open(io.BytesIO(response.content))
        image = _trim_white(image)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=88)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Imagen inválida: {exc}")

    return Response(
        content=buffer.getvalue(),
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
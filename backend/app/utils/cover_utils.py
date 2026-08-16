"""Detecció de portades placeholder de les biblioteques (DIBA)."""

import httpx

_PORTADESBD_HOST = "portadesbd.diba.cat"
_TIMEOUT = httpx.Timeout(10.0)
_PLACEHOLDER_CACHE: dict[str, bool] = {}


def _make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=_TIMEOUT)


async def is_placeholder_cover(url: str | None) -> bool:
    """True si `url` apunta a una portada placeholder (GIF) de portadesbd.

    Les portades reals de portadesbd.diba.cat es serveixen com a JPEG; quan el
    llibre no té cobertura digital la biblioteca retorna un placeholder que és
    un GIF 616x616 (amb `Content-Type: image/jpeg` enganyós). Per tant la
    detecció es fa pel magic bytes de la resposta.

    Les URL d'altres orígens (Google Books, OpenLibrary, ...) es consideren
    vàlides sense fer cap petició. El resultat es cachea en memòria per URL.
    """
    if not url or _PORTADESBD_HOST not in url:
        return False
    if url in _PLACEHOLDER_CACHE:
        return _PLACEHOLDER_CACHE[url]
    result = await _is_placeholder_gif(url)
    _PLACEHOLDER_CACHE[url] = result
    return result


async def _is_placeholder_gif(url: str) -> bool:
    try:
        async with _make_client() as client:
            response = await client.get(url, headers={"Range": "bytes=0-15"})
            if response.status_code != 200:
                return False
            return response.content.startswith(b"GIF89a")
    except httpx.HTTPError:
        return False

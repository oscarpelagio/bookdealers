"""Cliente Playwright headless contra Google Images.

Devuelve la primera imagen (grande) del resultado de búsqueda, o `None`
si Google bloquea (CAPTCHA), no hay resultados o falla la carga.

La instancia del navegador se crea una sola vez y se reutiliza.
"""

import asyncio
import os
import urllib.parse

from playwright.async_api import (
    async_playwright,
    Browser,
    Page,
)

from ..config import (
    TIMEOUT_MS,
    THUMB_WAIT_MS,
    USER_AGENT,
    VIEWPORT,
    CHROMIUM_ARGS,
    HEADLESS,
)

_browser: Browser | None = None
_start_lock = asyncio.Lock()

_LOGO_HINTS = (
    "gstatic.com/img/branding",
    "googlelogo",
    "logo_g",
    "googleg",
    ".svg",
    "google-refresh",
)


async def _get_browser() -> Browser:
    global _browser
    if _browser is None:
        async with _start_lock:
            if _browser is None:
                pw = await async_playwright().start()
                # Fusión del env: garantizamos DISPLAY=:99 para el modo headed
                # (el reloader de uvicorn a veces no lo propaga) sin pisar PATH.
                env = {}
                env.update(os.environ)
                env.setdefault("DISPLAY", ":99")
                _browser = await pw.chromium.launch(
                    headless=HEADLESS,
                    args=CHROMIUM_ARGS,
                    env=env,
                )
    return _browser


async def _close_consent(page: Page) -> None:
    """Cierra los diálogos de cookies/consentimiento si aparecen."""
    try:
        over18 = page.get_by_role("button", name="Sí, acepto")
        if await over18.count():
            await over18.first.click(timeout=2000)
        for label in ("Aceptar todo", "Accept all", "Aceptar"):
            accept = page.get_by_role("button", name=label)
            if await accept.count():
                await accept.first.click(timeout=2000)
                return
    except Exception:
        pass


async def _first_og_image(page: Page) -> str | None:
    try:
        meta = page.locator('meta[property="og:image"]')
        if await meta.count() == 0:
            return None
        value = await meta.first.get_attribute("content")
        if value and value.startswith("http"):
            return value
    except Exception:
        return None
    return None


async def _click_first_thumbnail_and_get_large(page: Page) -> str | None:
    """Clic en la primera miniatura real y lectura de la imagen grande del visor."""
    try:
        target, wrap = await _pick_thumbnail(page)
        clickable = wrap if wrap is not None else target
        if clickable is None:
            return None
        await clickable.click(timeout=THUMB_WAIT_MS)
        await page.wait_for_timeout(1500)
    except Exception:
        pass

    # Visor: clases clásicas del lightbox y cualquier img grande (>= 300px).
    for sel in ("img.n3VNCb", "img.sFlh5c"):
        try:
            loc = page.locator(sel).first
            if await loc.count():
                src = await loc.get_attribute("src")
                if src and src.startswith("http"):
                    return src
        except Exception:
            pass

    try:
        best = 0
        src_best = None
        imgs = page.locator("img")
        count = await imgs.count()
        for i in range(min(count, 180)):
            src = await imgs.nth(i).get_attribute("src") or ""
            srcset = await imgs.nth(i).get_attribute("srcset") or ""
            candidate = srcset.split(",")[0].split(" ")[0] if srcset.startswith("http") else src
            if not candidate.startswith("http") or any(h in candidate for h in _LOGO_HINTS):
                continue
            box = await imgs.nth(i).bounding_box()
            if box and box["width"] and box["width"] >= 300 and box["width"] > best:
                best = box["width"]
                src_best = candidate
        if src_best:
            return src_best
    except Exception:
        pass
    return None


async def _pick_thumbnail(page: Page):
    """Primera miniatura real del grid (nuevo diseño `udm=2`: `div[jsname] img`)."""
    thumbs = page.locator("div[jsname] img")
    count = await thumbs.count()
    if count:
        try:
            first = thumbs.first
            wrap = first.locator("xpath=ancestor::a[1]")
            if await wrap.count():
                return first, wrap
            return first, None
        except Exception:
            pass

    best = None
    best_area = 0
    imgs = page.locator("img")
    count = await imgs.count()
    for i in range(min(count, 200)):
        src = await imgs.nth(i).get_attribute("src") or ""
        data_src = await imgs.nth(i).get_attribute("data-src") or ""
        candidate = data_src if data_src.startswith("http") else src
        if not candidate.startswith("http"):
            continue
        if any(h in candidate for h in _LOGO_HINTS):
            continue
        box = await imgs.nth(i).bounding_box()
        if not box or not box["width"] or not box["height"]:
            continue
        if box["width"] < 60 or box["height"] < 60:
            continue
        area = box["width"] * box["height"]
        if area > best_area:
            best_area = area
            best = imgs.nth(i)
    return best, None


class Client:
    """Cliente para obtener la primera imagen del buscador Google Images."""

    async def search_image(self, author: str) -> dict:
        browser = await _get_browser()
        query = urllib.parse.quote(author.strip())
        url = f"https://www.google.com/search?q={query}&tbm=isch&hl=es&gl=es"

        try:
            context = await browser.new_context(
                user_agent=USER_AGENT,
                locale="es-ES",
                viewport=VIEWPORT,
                extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)

                if "sorry" in page.url:
                    return {"image_url": None, "source_url": None, "state": "blocked"}

                if "consent" in page.url:
                    await _close_consent(page)
                    await page.wait_for_timeout(800)

                image_url = await _first_og_image(page)
                if not image_url:
                    # Espera a que pinte la primera miniatura de resultados.
                    try:
                        await page.locator("img").first.wait_for(
                            state="visible", timeout=THUMB_WAIT_MS
                        )
                    except Exception:
                        pass
                    image_url = await _click_first_thumbnail_and_get_large(page)

                if not image_url:
                    return {"image_url": None, "source_url": None, "state": "missing"}

                source_url = await _result_source(page)
                return {"image_url": image_url, "source_url": source_url, "state": "ok"}
            finally:
                await context.close()
        except Exception as exc:
            print(f"[photo-scraper] error para '{author}': {exc!r}")
            return {"image_url": None, "source_url": None, "state": "error"}


async def _result_source(page: Page) -> str | None:
    """URL de la página de donde procede la imagen (mejor esfuerzo)."""
    try:
        first = page.locator('a[href^="/url"]').first
        if await first.count():
            href = await first.get_attribute("href") or ""
            return urllib.parse.unquote(href.replace("/url?q=", "").split("&")[0]) or None
    except Exception:
        pass
    return None
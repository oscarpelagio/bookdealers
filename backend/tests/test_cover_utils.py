"""Tests de detecció de portades placeholder (portadesbd DIBA)."""

import httpx
import pytest

from app.utils import cover_utils


@pytest.fixture(autouse=True)
def _clear_placeholder_cache():
    """Aïlla la caché global del mòdul entre tests (pytest-randomly reordena)."""
    cover_utils._PLACEHOLDER_CACHE.clear()
    yield
    cover_utils._PLACEHOLDER_CACHE.clear()


def _monkeypatch_client(monkeypatch, handler):
    monkeypatch.setattr(
        cover_utils,
        "_make_client",
        lambda: httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=httpx.Timeout(5.0)
        ),
    )
    cover_utils._PLACEHOLDER_CACHE.clear()


def _gif_handler(request):
    return httpx.Response(200, content=b"GIF89a..." + b"\x00" * 100)


def _jpeg_handler(request):
    return httpx.Response(200, content=b"\xff\xd8\xff\xe0JFIF.....")


async def test_non_portadesbd_url_is_not_placeholder(monkeypatch):
    def handler(request):
        raise AssertionError("no network for foreign URLs")

    _monkeypatch_client(monkeypatch, handler)
    assert await cover_utils.is_placeholder_cover("https://books.google.com/cover.jpg") is False
    assert await cover_utils.is_placeholder_cover(None) is False


async def test_placeholder_gif_detected(monkeypatch):
    _monkeypatch_client(monkeypatch, _gif_handler)
    url = "https://portadesbd.diba.cat/img.php?i=bib_00000064"
    assert await cover_utils.is_placeholder_cover(url) is True


async def test_real_jpeg_cover_not_placeholder(monkeypatch):
    _monkeypatch_client(monkeypatch, _jpeg_handler)
    url = "https://portadesbd.diba.cat/img.php?i=bib_00012345"
    assert await cover_utils.is_placeholder_cover(url) is False


async def test_result_is_cached_per_url(monkeypatch):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, content=b"GIF89a...")

    _monkeypatch_client(monkeypatch, handler)
    url = "https://portadesbd.diba.cat/img.php?i=bib_cached"
    assert await cover_utils.is_placeholder_cover(url) is True
    assert await cover_utils.is_placeholder_cover(url) is True
    assert calls["n"] == 1

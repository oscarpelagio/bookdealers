"""Tests del proxy de miniatures de Penguin (trim de marges blancs, sense xarxa)."""

from io import BytesIO

from PIL import Image, ImageDraw

from app.router.endpoints.thumb_router import _is_allowed, _trim_white


def test_trim_white_crops_synthetic():
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([100, 60, 300, 340], fill=(30, 40, 200))
    out = _trim_white(img)
    assert out.size == (203, 283)


def test_trim_white_noop_without_borders():
    img = Image.new("RGB", (300, 200), (10, 60, 120))
    out = _trim_white(img)
    assert out.size == img.size


def test_trim_white_pure_white_unchanged():
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    out = _trim_white(img)
    assert out.size == img.size


def test_trim_white_roundtrips_jpeg():
    img = Image.new("RGB", (400, 400), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([120, 80, 260, 320], fill=(200, 30, 40))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    out = _trim_white(Image.open(buf))
    assert out.size[0] < 400 and out.size[1] < 400


def test_is_allowed():
    assert _is_allowed("https://www.penguinlibros.com/es/c/1234-x.jpg")
    assert _is_allowed("https://penguinlibros.com/x.webp")
    assert _is_allowed("http://cdn.penguinlibros.com/x.jpg")
    assert not _is_allowed("https://evil.com/x.jpg")
    assert not _is_allowed("https://penguinlibros.com.evil.com/x.jpg")
    assert not _is_allowed("ftp://penguinlibros.com/x.jpg")
    assert not _is_allowed("not-a-url")
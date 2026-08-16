"""Tests de la paginación por cursor (core.pagination)."""

import base64
import uuid
from datetime import datetime, timezone

from app.core.pagination import build_page, decode_cursor, encode_cursor


def test_cursor_roundtrip():
    dt = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
    uid = uuid.uuid4()
    cursor = encode_cursor(dt, uid)
    decoded = decode_cursor(cursor)
    assert decoded is not None
    decoded_dt, decoded_id = decoded
    assert decoded_dt == dt
    assert decoded_id == uid


def test_cursor_survives_url_encoding():
    dt = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
    cursor = encode_cursor(dt, uuid.uuid4())
    assert "/" not in cursor
    assert "+" not in cursor
    assert decode_cursor(cursor) is not None


def test_cursor_accepts_int_id():
    dt = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
    decoded = decode_cursor(encode_cursor(dt, 123))
    assert decoded is not None
    assert decoded[1] == 123


def test_decode_invalid_cursor_returns_none():
    assert decode_cursor(None) is None
    assert decode_cursor("") is None
    assert decode_cursor("not-a-cursor") is None
    assert decode_cursor("!!!") is None


def test_decode_tampered_cursor_returns_none():
    dt = datetime(2026, 8, 5, tzinfo=timezone.utc)
    # Base64 válido pero con prefijo distinto al esperado por la app
    forged = base64.urlsafe_b64encode(
        f"xx:{dt.isoformat()}:{uuid.uuid4()}".encode("utf-8")
    ).decode("ascii")
    assert decode_cursor(forged) is None


def test_build_page_shape():
    page = build_page(["a", "b"], "abc123")
    assert page == {"items": ["a", "b"], "next": "abc123"}
    page2 = build_page([], None)
    assert page2["next"] is None

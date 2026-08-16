"""Tests del flux de Google login."""

from sqlmodel import select

from app.auth.models import User
from tests.conftest import random_email, valid_password


async def test_google_login_creates_user(client, google_verifier, db_session):
    resp = await client.post("/auth/google", json={"credential": "fake.id.token"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["refresh_token"]

    user = (
        await db_session.exec(select(User).where(User.google_sub == "google-sub-123"))
    ).first()
    assert user is not None
    assert user.email == "google.user@example.com"
    assert user.is_email_verified is True


async def test_google_login_existing_user(client, google_verifier, db_session):
    email = "google.user@example.com"
    payload = {
        "email": email,
        "username": "existinguser",
        "password": valid_password(),
    }
    await client.post("/auth/register", json=payload)

    resp = await client.post("/auth/google", json={"credential": "fake.id.token"})
    assert resp.status_code == 200

    user = (
        await db_session.exec(select(User).where(User.email == email))
    ).first()
    assert user is not None
    # La cuenta existente queda vinculada al identificador de Google.
    assert user.google_sub == "google-sub-123"


async def test_google_login_invalid_token(client, google_verifier):
    google_verifier.should_fail = True
    resp = await client.post("/auth/google", json={"credential": "fake.id.token"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "google_token_invalid"


async def test_google_login_returns_backend_jwt(client, google_verifier):
    resp = await client.post("/auth/google", json={"credential": "fake.id.token"})
    assert resp.status_code == 200
    data = resp.json()

    import jwt as pyjwt

    from app.core.config import settings

    decoded = pyjwt.decode(
        data["access_token"],
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert decoded["sub"]
    assert "USER" in decoded["roles"]

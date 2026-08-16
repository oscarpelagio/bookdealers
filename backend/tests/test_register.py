"""Tests del flux de registre."""

from sqlmodel import select

from app.auth.models import User
from tests.conftest import random_email, valid_password


def _register_payload(
    email: str | None = None,
    username: str = "newuser",
    password: str | None = None,
    full_name: str | None = "New User",
) -> dict:
    return {
        "email": email or random_email(),
        "username": username,
        "password": password or valid_password(),
        "full_name": full_name,
    }


async def test_register_success(client):
    payload = _register_payload()
    resp = await client.post("/auth/register", json=payload)

    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == payload["email"]
    assert data["user"]["username"] == "newuser"
    assert data["user"]["roles"] == ["USER"]
    assert data["requires_email_verification"] is True
    # EMAIL_SEND_ENABLED=false → se devuelve la URL de verificación (dev)
    assert "verify-email" in (data["dev_verification_url"] or "")


async def test_register_normalizes_email_and_username(client, db_session):
    resp = await client.post(
        "/auth/register",
        json=_register_payload(email="  User@Example.COM ", username="  New.User "),
    )
    assert resp.status_code == 201
    user = (
        await db_session.exec(select(User).where(User.email == "user@example.com"))
    ).first()
    assert user is not None
    assert user.username == "New.User"
    assert user.email == "user@example.com"


async def test_register_does_not_store_plaintext_password(client, db_session):
    payload = _register_payload()
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201

    user = (
        await db_session.exec(select(User).where(User.email == payload["email"]))
    ).first()
    assert user is not None
    assert user.hashed_password != payload["password"]
    assert user.hashed_password.startswith("$argon2id$")


async def test_register_duplicate_email_is_not_revealed(client):
    email = random_email()
    first = await client.post("/auth/register", json=_register_payload(email=email))
    assert first.status_code == 201
    assert "verify-email" in (first.json()["dev_verification_url"] or "")

    second = await client.post(
        "/auth/register", json=_register_payload(email=email, username="another")
    )
    # Misma forma de respuesta: no se revela que el email existe.
    assert second.status_code == 201
    assert second.json()["dev_verification_url"] is None


async def test_register_duplicate_username_is_not_revealed(client):
    username = "takenuser"
    first = await client.post(
        "/auth/register", json=_register_payload(username=username)
    )
    assert first.status_code == 201

    second = await client.post(
        "/auth/register", json=_register_payload(email=random_email(), username=username)
    )
    assert second.status_code == 201
    assert second.json()["dev_verification_url"] is None


async def test_register_rejects_invalid_email(client):
    resp = await client.post("/auth/register", json=_register_payload(email="not-an-email"))
    assert resp.status_code == 422


async def test_register_rejects_invalid_username(client):
    resp = await client.post(
        "/auth/register", json=_register_payload(username="in-valid!")
    )
    assert resp.status_code == 422


async def test_register_rejects_weak_password(client):
    weak_passwords = [
        "short1A!",
        "onlylowercase1!",
        "ONLYUPPERCASE1!",
        "NoDigitsHere!",
        "NoSymbolsHere1",
    ]
    for password in weak_passwords:
        resp = await client.post(
            "/auth/register", json=_register_payload(password=password)
        )
        assert resp.status_code == 422, password


async def test_register_assigns_user_role(client, db_session):
    email = random_email()
    await client.post("/auth/register", json=_register_payload(email=email))

    from app.auth.models import Role, UserRole

    user = (
        await db_session.exec(select(User).where(User.email == email))
    ).first()
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    roles = list((await db_session.exec(stmt)).all())
    assert roles == ["USER"]

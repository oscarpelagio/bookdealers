"""Tests de permisos (endpoints protegits + RBAC)."""

from tests.conftest import create_user, random_email, valid_password


async def test_me_requires_authentication(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token(client):
    resp = await client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-valid-jwt"}
    )
    assert resp.status_code == 401


async def test_me_returns_current_user(client):
    email = random_email()
    payload = {
        "email": email,
        "username": "meprofile",
        "password": valid_password(),
    }
    await client.post("/auth/register", json=payload)
    login = await client.post(
        "/auth/login", json={"email": email, "password": valid_password()}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == email
    assert data["username"] == "meprofile"
    assert data["roles"] == ["USER"]


async def test_admin_endpoint_rejects_user_role(client, session_factory):
    from fastapi import APIRouter, Depends

    from app.auth.dependencies import require_roles
    from app.auth.models import RoleKey
    from app.auth.schemas import MessageResponse
    from app.main import app

    router = APIRouter()

    @router.get("/_test/admin-only", response_model=MessageResponse)
    async def admin_only(
        user=Depends(require_roles(RoleKey.ADMIN)),
    ) -> MessageResponse:
        return MessageResponse(message="admin")

    app.include_router(router)
    try:
        # Usuario con rol USER → 403.
        email = random_email()
        await client.post(
            "/auth/register",
            json={"email": email, "username": "rbacuser", "password": valid_password()},
        )
        login = await client.post(
            "/auth/login", json={"email": email, "password": valid_password()}
        )
        user_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        denied = await client.get("/_test/admin-only", headers=user_headers)
        assert denied.status_code == 403

        # Usuario con rol ADMIN → 200.
        admin = await create_user(
            session_factory,
            email=random_email(),
            username="rbacadmin",
            roles=[RoleKey.ADMIN],
        )
        admin_login = await client.post(
            "/auth/login",
            json={"email": admin.email, "password": valid_password()},
        )
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
        allowed = await client.get("/_test/admin-only", headers=admin_headers)
        assert allowed.status_code == 200
        assert allowed.json()["message"] == "admin"
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != "/_test/admin-only"
        ]

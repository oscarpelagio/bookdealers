"""Validació d'ID tokens de Google (infraestructura).

El frontend obté el credential via Google Identity Services i l'envia
al backend. Aquí es verifica la signatura contra la JWKS pública de
Google (iss/aud/exp) i es retorna la identitat verificada. Els tokens
de Google mai s'usen per autoritzar peticions internes.
"""

import asyncio
import time
from dataclasses import dataclass

import httpx
import jwt

from app.auth.exceptions import GoogleTokenInvalidError
from app.core.config import settings

_JWKS_TTL_SECONDS = 3600


@dataclass(frozen=True)
class GoogleUserInfo:
    sub: str
    email: str
    name: str | None
    email_verified: bool


class GoogleIdTokenVerifier:
    def __init__(
        self,
        *,
        client_id: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client_id = client_id or settings.google_client_id
        self._http_client = http_client
        self._jwks: dict[str, dict] = {}
        self._jwks_fetched_at: float = 0.0
        self._lock = asyncio.Lock()

    async def verify(self, id_token: str) -> GoogleUserInfo:
        if not self._client_id:
            raise GoogleTokenInvalidError(
                "Google login is not configured.", code="google_not_configured"
            )

        unverified_payload = self._decode_unverified(id_token)
        issuer = unverified_payload.get("iss")
        if issuer not in settings.google_issuers:
            raise GoogleTokenInvalidError("Invalid issuer.")

        header = jwt.get_unverified_header(id_token)
        public_key = await self._get_public_key(header.get("kid"))
        if public_key is None:
            raise GoogleTokenInvalidError("Signing key not found.")

        try:
            payload = jwt.decode(
                id_token,
                public_key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=settings.google_issuers,
                options={"verify_exp": True, "verify_iat": True},
            )
        except jwt.PyJWTError as exc:
            raise GoogleTokenInvalidError(str(exc)) from exc

        email = payload.get("email")
        if not email:
            raise GoogleTokenInvalidError("Email claim missing.")

        return GoogleUserInfo(
            sub=str(payload["sub"]),
            email=email.lower(),
            name=payload.get("name"),
            email_verified=bool(payload.get("email_verified", False)),
        )

    def _decode_unverified(self, id_token: str) -> dict:
        try:
            return jwt.decode(
                id_token,
                options={"verify_signature": False, "verify_exp": False},
            )
        except jwt.PyJWTError as exc:
            raise GoogleTokenInvalidError(str(exc)) from exc

    async def _get_public_key(self, kid: str | None) -> str | None:
        if kid is None:
            return None
        if self._is_jwks_fresh() and kid in self._jwks:
            return self._jwks[kid]
        async with self._lock:
            if self._is_jwks_fresh() and kid in self._jwks:
                return self._jwks[kid]
            await self._refresh_jwks()
            return self._jwks.get(kid)

    def _is_jwks_fresh(self) -> bool:
        return bool(self._jwks) and (time.monotonic() - self._jwks_fetched_at) < _JWKS_TTL_SECONDS

    async def _refresh_jwks(self) -> None:
        client = self._http_client
        try:
            if client is None:
                async with httpx.AsyncClient(timeout=10) as created:
                    await self._fetch_into(created)
            else:
                await self._fetch_into(client)
        except httpx.HTTPError as exc:
            raise GoogleTokenInvalidError("Could not fetch Google keys.") from exc

    async def _fetch_into(self, client: httpx.AsyncClient) -> None:
        response = await client.get(settings.google_jwks_url)
        response.raise_for_status()
        keys: list[dict] = response.json().get("keys", [])
        self._jwks = {k["kid"]: k for k in keys if "kid" in k}
        self._jwks_fetched_at = time.monotonic()

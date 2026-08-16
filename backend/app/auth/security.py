"""Capa d'infraestructura de seguretat.

- Hashing de contrasenyes amb Argon2id (pwdlib).
- JWT Access Tokens (PyJWT).
- Hashing de refresh/verification/reset tokens (HMAC-SHA256 amb pepper).
- Generació de secrets criptogràfics.

Aquesta capa no conté lògica de negoci: el domini (service.py) hi delega
operacions criptogràfiques concretes.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings

# ---------- Contrasenyes (Argon2id) ----------

_password_hasher = PasswordHash(
    hashers=[
        Argon2Hasher(
            time_cost=settings.argon2_time_cost,
            memory_cost=settings.argon2_memory_cost,
            parallelism=settings.argon2_parallelism,
        )
    ]
)


def hash_password(password: str) -> str:
    """Retorna el hash Argon2id de la contrasenya."""
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica una contrasenya contra el seu hash. Mai llença excepcions."""
    try:
        return _password_hasher.verify(password, hashed_password)
    except Exception:
        return False


# ---------- Refresh / one-time tokens ----------


def create_token_hash(token: str) -> str:
    """HMAC-SHA256 del token emprant el secret (pepper) de configuració.

    Els tokens opacs mai s'emmagatzemen en clar: només el seu hash.
    El pepper impedeix que un hash filtrat sigui brute-forceable.
    """
    secret = settings.token_hash_secret.get_secret_value().encode("utf-8")
    return hmac.new(secret, token.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_refresh_token() -> str:
    """Genera un refresh token opac d'alta entropia (48 bytes aleatoris)."""
    return secrets.token_urlsafe(48)


def generate_one_time_token() -> str:
    """Genera un token d'ús únic (verificació de correu / reset)."""
    return secrets.token_urlsafe(32)


# ---------- JWT Access Tokens ----------


def create_access_token(
    user_id: str,
    roles: list[str],
    *,
    device_id: str | None = None,
) -> tuple[str, datetime]:
    """Crea un JWT d'accés i retorna (token, expires_at)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "device_id": device_id,
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Decodifica i valida un JWT d'accés.

    Llença `jwt.PyJWTError` si la signatura, `iss`, `aud` o `exp` fallen.
    """
    return jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "jti", "iat", "exp", "type"]},
    )


def utcnow() -> datetime:
    """Datetime actual timezone-aware en UTC."""
    return datetime.now(timezone.utc)

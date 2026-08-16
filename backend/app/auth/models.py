"""Models de dades del mòdul d'autenticació.

Disseny:
- `roles` i `user_roles`: RBAC normalitzat preparat per a permisos futurs.
- `users`: usuari amb soft delete i bloqueig per força bruta.
- `refresh_tokens`: tokens opacs, hashejats, amb famílies per detectar replay.
- `email_verification_tokens` / `password_reset_tokens`: tokens d'ús únic.

Tots els timestamps són timezone-aware (UTC).
"""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlmodel import SQLModel, Field

from app.auth.security import utcnow


def _auth_datetime(required: bool = False):
    """Column DateTime timezone-aware amb default UTC."""
    return Column(DateTime(timezone=True), nullable=not required, default=utcnow)


class RoleKey(str, Enum):
    """Claus dels rols disponibles al sistema."""

    USER = "USER"
    ADMIN = "ADMIN"


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    name: str = Field(
        sa_column=Column(String(50), nullable=False, unique=True, index=True)
    )
    description: str | None = Field(default=None, sa_column=Column(String(255)))
    created_at: datetime = Field(sa_column=_auth_datetime(required=True))


class UserRole(SQLModel, table=True):
    """Taula d'unió N:N entre usuaris i rols."""

    __tablename__ = "user_roles"

    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    role_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
        )
    )
    created_at: datetime = Field(sa_column=_auth_datetime(required=True))


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        # Uniqueness només sobre usuaris actius (no eliminats), via índexs parcials.
        Index(
            "uq_users_email_active",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_users_username_active",
            "username",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_users_google_sub_active",
            "google_sub",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Búsqueda social (F10): GIN trigram sobre el handle (username).
        Index(
            "ix_users_username_trgm",
            "username",
            postgresql_using="gin",
            postgresql_ops={"username": "gin_trgm_ops"},
        ),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    email: str = Field(
        default=None, sa_column=Column(String(320), nullable=False, index=True)
    )
    username: str = Field(
        default=None, sa_column=Column(String(30), nullable=False, index=True)
    )
    full_name: str | None = Field(default=None, sa_column=Column(String(120)))
    hashed_password: str | None = Field(default=None, sa_column=Column(String(255)))
    # Identificador d'OAuth de Google (sub) si l'usuari va entrar amb Google.
    google_sub: str | None = Field(
        default=None, sa_column=Column(String(255), index=True)
    )
    is_email_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    failed_login_attempts: int = Field(default=0)
    locked_until: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    last_login_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    created_at: datetime = Field(sa_column=_auth_datetime(required=True))
    updated_at: datetime = Field(sa_column=_auth_datetime(required=True))
    deleted_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )


class RefreshToken(SQLModel, table=True):
    """Refresh token opac, emmagatzemat únicament hashejat.

    - `family_id` agrupa tota la cadena de rotació originada pel mateix login.
    - `parent_id` apunta al token que va generar aquest (rotació). Ambdós
      permeten auditar cadenes i detectar replays.
    - Columnes d'auditoria: IP/User-Agent de creació i del darrer ús.
    """

    __tablename__ = "refresh_tokens"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    token_hash: str = Field(
        sa_column=Column(String(64), nullable=False, unique=True, index=True)
    )
    family_id: uuid.UUID = Field(
        sa_column=Column(PgUUID(as_uuid=True), nullable=False, index=True)
    )
    # Token del qual prové aquest (None per al primer de la cadena).
    parent_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
        ),
    )
    device_id: str | None = Field(default=None, sa_column=Column(String(255)))
    created_user_agent: str | None = Field(default=None, sa_column=Column(String(500)))
    created_ip_address: str | None = Field(default=None, sa_column=Column(String(45)))
    last_used_user_agent: str | None = Field(default=None, sa_column=Column(String(500)))
    last_used_ip_address: str | None = Field(default=None, sa_column=Column(String(45)))
    issued_at: datetime = Field(sa_column=_auth_datetime(required=True))
    last_used_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    revoked_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    created_at: datetime = Field(sa_column=_auth_datetime(required=True))


class EmailVerificationToken(SQLModel, table=True):
    """Token d'ús únic per verificar el correu de l'usuari."""

    __tablename__ = "email_verification_tokens"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    token_hash: str = Field(
        sa_column=Column(String(64), nullable=False, unique=True, index=True)
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    used_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    created_at: datetime = Field(sa_column=_auth_datetime(required=True))


class PasswordResetToken(SQLModel, table=True):
    """Token d'ús únic per recuperar la contrasenya."""

    __tablename__ = "password_reset_tokens"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PgUUID(as_uuid=True), primary_key=True),
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            PgUUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    token_hash: str = Field(
        sa_column=Column(String(64), nullable=False, unique=True, index=True)
    )
    expires_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    used_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    created_at: datetime = Field(sa_column=_auth_datetime(required=True))
"""Servei de domini d'autenticació.

Conté tota la lògica de negoci (registre, login, refresh amb rotació,
logout, Google, verificació de correu i reset de contrasenya) sense cap
lògic de capa HTTP ni de persistència directa.
"""

import logging
import re
import secrets
import uuid
from datetime import timedelta

from app.auth import security
from app.auth.exceptions import (
    EmailVerificationError,
    GoogleTokenInvalidError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
    TokenNotFoundError,
    TokenRevokedError,
    TooManyAttemptsError,
    UserDisabledError,
)
from app.auth.google import GoogleIdTokenVerifier
from app.auth.models import RoleKey, User
from app.auth.repository import AuthRepository
from app.auth.schemas import (
    GoogleLoginRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenPair,
    UserResponse,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

_dummy_hash: str | None = None


def _get_dummy_hash() -> str:
    """Hash fix per igualar el cost temporal del login quan l'email no existeix."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = security.hash_password(secrets.token_urlsafe(24))
    return _dummy_hash


def is_dev() -> bool:
    """Només en entorn development amb debug actiu s'exposen tokens de dev."""
    return settings.env.strip().lower() == "development" and settings.debug


class AuthService:
    def __init__(self, repo: AuthRepository) -> None:
        self.repo = repo

    # ---------- Registre ----------

    async def register(
        self,
        data: RegisterRequest,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> RegisterResponse:
        """Registra un usuari.

        No revela si l'email/username ja existeix: si hi ha conflicte es
        retorna la mateixa resposta genèrica sense crear l'usuari.
        """
        existing_by_email = await self.repo.get_by_email(data.email)
        existing_by_username = await self.repo.get_by_username(data.username)
        if existing_by_email is not None or existing_by_username is not None:
            return RegisterResponse(
                user=await self._user_response(existing_by_email or existing_by_username),
                requires_email_verification=True,
                dev_verification_url=None,
                dev_reset_url=None,
            )

        hashed_password = security.hash_password(data.password)
        user = await self.repo.create_user(
            email=data.email,
            username=data.username,
            hashed_password=hashed_password,
            full_name=data.full_name,
        )
        raw_token = await self._create_email_verification_token(user)
        dev_url = None
        if not settings.email_send_enabled and self._is_dev():
            dev_url = self._verification_url(raw_token)
        return RegisterResponse(
            user=await self._user_response(user),
            requires_email_verification=True,
            dev_verification_url=dev_url,
            dev_reset_url=None,
        )

    # ---------- Login ----------

    async def login(
        self,
        data: LoginRequest,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        user = await self.repo.get_by_email(data.email)

        if user is None:
            security.verify_password(data.password, _get_dummy_hash())
            raise InvalidCredentialsError()

        if not user.is_active or user.deleted_at is not None:
            security.verify_password(data.password, _get_dummy_hash())
            raise InvalidCredentialsError()

        if user.locked_until is not None and user.locked_until > security.utcnow():
            raise TooManyAttemptsError()

        if user.hashed_password is None or not security.verify_password(
            data.password, user.hashed_password
        ):
            await self._register_failed_attempt(user)
            raise InvalidCredentialsError()

        await self.repo.record_login(user)
        return await self._issue_token_pair(user, data.device_id, user_agent, ip_address)

    # ---------- Refresh (rotació + protecció replay) ----------

    async def refresh(
        self,
        data: RefreshRequest,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        token_hash = security.create_token_hash(data.refresh_token)
        stored = await self.repo.get_refresh_token_by_hash(token_hash)

        if stored is None:
            raise TokenInvalidError()

        if stored.revoked_at is not None:
            # Replay d'un token ja rotat: senyal de token robat. Revoca tota la família.
            logger.warning("Refresh token replay detected (family=%s)", stored.family_id)
            await self.repo.revoke_family(stored.family_id)
            await self.repo.commit()
            raise TokenRevokedError()

        if stored.expires_at <= security.utcnow():
            await self.repo.revoke_refresh_token(stored)
            await self.repo.commit()
            raise TokenExpiredError()

        user = await self.repo.get_by_id(stored.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise TokenRevokedError()

        # Rotació: registre d'ús del token actual, nou token amb parent i
        # revocació de l'antic (mateixa família).
        await self.repo.record_refresh_used(
            stored,
            last_used_ip_address=ip_address,
            last_used_user_agent=user_agent,
        )
        raw_token = security.generate_refresh_token()
        new_hash = security.create_token_hash(raw_token)
        new_expiry = security.utcnow() + timedelta(days=settings.refresh_token_expire_days)
        new_device = data.device_id or stored.device_id
        new_token = await self.repo.create_refresh_token(
            user_id=user.id,
            token_hash=new_hash,
            family_id=stored.family_id,
            parent_id=stored.id,
            expires_at=new_expiry,
            device_id=new_device,
            created_user_agent=user_agent,
            created_ip_address=ip_address,
        )
        await self.repo.revoke_refresh_token(stored)
        await self.repo.commit()

        roles = await self.repo.get_user_roles(user.id)
        access_token, expires_at = security.create_access_token(
            str(user.id), roles, device_id=new_device
        )
        return self._token_pair(
            access_token=access_token,
            refresh_token=raw_token,
            expires_at=expires_at,
        )

    # ---------- Logout ----------

    async def logout(self, data: LogoutRequest) -> None:
        token_hash = security.create_token_hash(data.refresh_token)
        stored = await self.repo.get_refresh_token_by_hash(token_hash)
        if stored is None:
            return
        if data.logout_everywhere:
            await self.repo.revoke_all_user_tokens(stored.user_id)
        else:
            await self.repo.revoke_refresh_token(stored)
        await self.repo.commit()

    # ---------- Google ----------

    async def google_login(
        self,
        data: GoogleLoginRequest,
        verifier: GoogleIdTokenVerifier,
        *,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        info = await verifier.verify(data.credential)

        if settings.google_require_email_verified and not info.email_verified:
            raise GoogleTokenInvalidError("Google email is not verified.")

        user = await self.repo.get_by_google_sub(info.sub)
        if user is None:
            user = await self.repo.get_by_email(info.email)
            if user is not None:
                # Vincula la cuenta de Google amb l'usuari existent.
                user.google_sub = info.sub
                if info.email_verified:
                    user.is_email_verified = True
                await self.repo.update_user(user)
            else:
                username = await self._unique_username_from_email(info.email)
                user = await self.repo.create_user(
                    email=info.email,
                    username=username,
                    full_name=info.name,
                    google_sub=info.sub,
                    is_email_verified=info.email_verified,
                )

        if not user.is_active or user.deleted_at is not None:
            raise UserDisabledError()

        await self.repo.record_login(user)
        return await self._issue_token_pair(user, data.device_id, user_agent, ip_address)

    # ---------- Verificació de correu ----------

    async def verify_email(self, token: str) -> User:
        token_hash = security.create_token_hash(token)
        stored = await self.repo.get_email_verification_token(token_hash)
        if stored is None or stored.used_at is not None:
            raise EmailVerificationError("Invalid verification token.")
        if stored.expires_at <= security.utcnow():
            raise EmailVerificationError("Verification token has expired.")
        user = await self.repo.get_by_id(stored.user_id)
        if user is None:
            raise EmailVerificationError("User not found.")
        await self.repo.set_email_verified(user)
        await self.repo.mark_email_verification_used(stored)
        await self.repo.commit()
        return user

    # ---------- Recuperació de contrasenya ----------

    async def request_password_reset(self, email: str) -> str | None:
        user = await self.repo.get_by_email(email)
        if user is None:
            return None
        raw_token = security.generate_one_time_token()
        token_hash = security.create_token_hash(raw_token)
        expiry = security.utcnow() + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        await self.repo.create_password_reset_token(
            user_id=user.id, token_hash=token_hash, expires_at=expiry
        )
        await self.repo.commit()
        self._send_email(user.email, raw_token=raw_token, kind="password_reset")
        return raw_token

    async def reset_password(self, token: str, new_password: str) -> None:
        token_hash = security.create_token_hash(token)
        stored = await self.repo.get_password_reset_token(token_hash)
        if stored is None or stored.used_at is not None:
            raise TokenNotFoundError()
        if stored.expires_at <= security.utcnow():
            raise TokenNotFoundError()
        user = await self.repo.get_by_id(stored.user_id)
        if user is None:
            raise TokenNotFoundError()

        user.hashed_password = security.hash_password(new_password)
        await self.repo.mark_password_reset_used(stored)
        await self.repo.update_user(user)
        await self.repo.revoke_all_user_tokens(user.id)
        await self.repo.commit()

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        if user.hashed_password is None or not security.verify_password(
            current_password, user.hashed_password
        ):
            raise InvalidCredentialsError("Current password is incorrect.")
        user.hashed_password = security.hash_password(new_password)
        await self.repo.update_user(user)
        await self.repo.revoke_all_user_tokens(user.id)
        await self.repo.commit()

    # ---------- Perfil ----------

    async def get_user_response(self, user_id: uuid.UUID) -> UserResponse:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise TokenInvalidError()
        return await self._user_response(user)

    # ---------- Helpers privats ----------

    async def _create_email_verification_token(self, user: User) -> str:
        raw_token = security.generate_one_time_token()
        token_hash = security.create_token_hash(raw_token)
        expiry = security.utcnow() + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        await self.repo.create_email_verification_token(
            user_id=user.id, token_hash=token_hash, expires_at=expiry
        )
        await self.repo.commit()
        self._send_email(user.email, raw_token=raw_token, kind="email_verification")
        return raw_token

    async def _issue_token_pair(
        self,
        user: User,
        device_id: str | None,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        roles = await self.repo.get_user_roles(user.id)
        access_token, expires_at = security.create_access_token(
            str(user.id), roles, device_id=device_id
        )
        raw_token = security.generate_refresh_token()
        token_hash = security.create_token_hash(raw_token)
        refresh_expiry = security.utcnow() + timedelta(
            days=settings.refresh_token_expire_days
        )
        await self.repo.create_refresh_token(
            user_id=user.id,
            token_hash=token_hash,
            family_id=uuid.uuid4(),
            parent_id=None,
            expires_at=refresh_expiry,
            device_id=device_id,
            created_user_agent=user_agent,
            created_ip_address=ip_address,
        )
        await self.repo.commit()
        return self._token_pair(access_token, raw_token, expires_at)

    def _token_pair(
        self, access_token: str, refresh_token: str, expires_at
    ) -> TokenPair:
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            access_token_expires_in=settings.access_token_expire_minutes * 60,
            refresh_token_expires_in=settings.refresh_token_expire_days * 86400,
            expires_at=expires_at,
        )

    async def _register_failed_attempt(self, user: User) -> None:
        attempts = user.failed_login_attempts + 1
        locked_until = None
        if attempts >= settings.login_max_attempts:
            locked_until = security.utcnow() + timedelta(
                seconds=settings.login_lockout_seconds
            )
        await self.repo.set_failed_login_state(
            user, failed_attempts=attempts, locked_until=locked_until
        )

    async def _unique_username_from_email(self, email: str) -> str:
        base = re.sub(r"[^a-zA-Z0-9_.]", "", email.split("@")[0])
        if not base:
            base = "user"
        base = base[:30]
        candidate = base
        suffix = 1
        while await self.repo.get_by_username(candidate):
            suffix += 1
            candidate = f"{base[:27]}{suffix}"
        return candidate

    def _verification_url(self, raw_token: str) -> str:
        return f"{settings.frontend_url}/auth/verify-email?token={raw_token}"

    async def _user_response(self, user: User) -> UserResponse:
        roles = await self.repo.get_user_roles(user.id)
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            roles=roles,
            is_email_verified=user.is_email_verified,
            is_active=user.is_active,
            created_at=user.created_at,
        )

    def _is_dev(self) -> bool:
        return is_dev()

    def _send_email(self, email: str, *, raw_token: str, kind: str) -> None:
        """Punt d'integració per al sistema de correu (encara no implementat).

        Quan l'enviament està desactivat, en mode dev es registra l'enllaç als
        logs per poder provar el flux. Els tokens mai es retornen al client en
        producció.
        """
        if settings.email_send_enabled:
            logger.info("email=%s kind=%s queued for sending", email, kind)
            return
        if self._is_dev():
            logger.warning(
                "email=%s kind=%s dev_link=%s%s (sending disabled)",
                email,
                kind,
                settings.frontend_url,
                f"/auth/verify-email?token={raw_token}"
                if kind == "email_verification"
                else f"/auth/reset-password?token={raw_token}",
            )
        else:
            logger.warning("email=%s kind=%s sending disabled", email, kind)


async def seed_default_roles() -> None:
    """Crea els rols bàsics (USER, ADMIN) si no existeixen. Idempotent."""
    from app.core.db import async_session

    async with async_session() as session:
        repo = AuthRepository(session)
        for role in RoleKey:
            existing = await repo.get_role_by_name(role.value)
            if existing is None:
                await repo.create_role(
                    role.value,
                    description=f"Default {role.value} role",
                )
        await session.commit()

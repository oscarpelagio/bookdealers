"""Repositori d'accés a dades del mòdul d'autenticació.

Únicament operacions de persistència; no conté lògica de negoci.
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, update
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
    Role,
    RoleKey,
    User,
    UserRole,
)
from app.auth.security import utcnow


class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Users ----------

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        return (await self.db.exec(stmt)).first()

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username, User.deleted_at.is_(None))
        return (await self.db.exec(stmt)).first()

    async def get_by_google_sub(self, google_sub: str) -> User | None:
        stmt = select(User).where(
            User.google_sub == google_sub, User.deleted_at.is_(None)
        )
        return (await self.db.exec(stmt)).first()

    async def create_user(
        self,
        *,
        email: str,
        username: str,
        hashed_password: str | None = None,
        full_name: str | None = None,
        google_sub: str | None = None,
        is_email_verified: bool = False,
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            google_sub=google_sub,
            is_email_verified=is_email_verified,
        )
        self.db.add(user)
        await self.db.flush()
        await self.add_roles(user.id, [RoleKey.USER])
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_user(self, user: User) -> User:
        user.updated_at = utcnow()
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def soft_delete(self, user: User) -> None:
        user.deleted_at = utcnow()
        user.is_active = False
        self.db.add(user)
        await self.db.commit()

    async def set_failed_login_state(
        self,
        user: User,
        *,
        failed_attempts: int,
        locked_until: datetime | None,
    ) -> None:
        user.failed_login_attempts = failed_attempts
        user.locked_until = locked_until
        user.updated_at = utcnow()
        self.db.add(user)
        await self.db.commit()

    async def record_login(self, user: User) -> None:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = utcnow()
        user.updated_at = utcnow()
        self.db.add(user)
        await self.db.commit()

    # ---------- Roles ----------

    async def get_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return (await self.db.exec(stmt)).first()

    async def create_role(self, name: str, description: str | None = None) -> Role:
        role = Role(name=name, description=description)
        self.db.add(role)
        await self.db.flush()
        return role

    async def add_roles(self, user_id: uuid.UUID, roles: list[RoleKey]) -> None:
        for role_key in roles:
            role = await self.get_role_by_name(role_key.value)
            if role is None:
                role = await self.create_role(role_key.value)
            existing = await self.db.exec(
                select(UserRole).where(
                    UserRole.user_id == user_id, UserRole.role_id == role.id
                )
            )
            if existing.first() is None:
                self.db.add(UserRole(user_id=user_id, role_id=role.id))
        await self.db.flush()

    async def get_user_roles(self, user_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return list((await self.db.exec(stmt)).all())

    # ---------- Refresh tokens ----------

    async def create_refresh_token(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        family_id: uuid.UUID,
        parent_id: uuid.UUID | None,
        expires_at: datetime,
        device_id: str | None,
        created_user_agent: str | None,
        created_ip_address: str | None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            family_id=family_id,
            parent_id=parent_id,
            expires_at=expires_at,
            device_id=device_id,
            created_user_agent=created_user_agent,
            created_ip_address=created_ip_address,
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return (await self.db.exec(stmt)).first()

    async def record_refresh_used(
        self,
        token: RefreshToken,
        *,
        last_used_ip_address: str | None,
        last_used_user_agent: str | None,
    ) -> None:
        token.last_used_at = utcnow()
        if last_used_ip_address is not None:
            token.last_used_ip_address = last_used_ip_address
        if last_used_user_agent is not None:
            token.last_used_user_agent = last_used_user_agent
        self.db.add(token)
        await self.db.flush()

    async def revoke_refresh_token(
        self,
        token: RefreshToken,
    ) -> None:
        token.revoked_at = utcnow()
        self.db.add(token)
        await self.db.flush()

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        now = utcnow()
        await self.db.exec(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self.db.flush()

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> None:
        now = utcnow()
        await self.db.exec(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        await self.db.flush()

    async def delete_expired_refresh_tokens(self) -> None:
        await self.db.exec(
            delete(RefreshToken).where(RefreshToken.expires_at < utcnow())
        )

    # ---------- Email verification tokens ----------

    async def create_email_verification_token(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_email_verification_token(
        self, token_hash: str
    ) -> EmailVerificationToken | None:
        stmt = select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash
        )
        return (await self.db.exec(stmt)).first()

    async def mark_email_verification_used(self, token: EmailVerificationToken) -> None:
        token.used_at = utcnow()
        self.db.add(token)
        await self.db.flush()

    async def set_email_verified(self, user: User) -> None:
        user.is_email_verified = True
        user.updated_at = utcnow()
        self.db.add(user)
        await self.db.flush()

    # ---------- Password reset tokens ----------

    async def create_password_reset_token(
        self,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(token)
        await self.db.flush()
        return token

    async def get_password_reset_token(self, token_hash: str) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash
        )
        return (await self.db.exec(stmt)).first()

    async def mark_password_reset_used(self, token: PasswordResetToken) -> None:
        token.used_at = utcnow()
        self.db.add(token)
        await self.db.flush()

    async def commit(self) -> None:
        await self.db.commit()

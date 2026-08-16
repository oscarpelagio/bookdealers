"""Repositorio de persistencia del módulo profiles.

Solo operaciones de base de datos; sin lógica de negocio.
"""

from __future__ import annotations

import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.time import utcnow
from app.profiles.models import PrivacySetting, Profile, ProfilePreference, ReadingGoal


class ProfileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Profile ----------

    async def get_by_user_id(self, user_id: uuid.UUID) -> Profile | None:
        stmt = select(Profile).where(Profile.user_id == user_id)
        return (await self.db.exec(stmt)).first()

    async def get_profile_with_user(
        self, handle: str
    ) -> tuple[User, Profile] | None:
        """Resuelve `(User activo, Profile)` por handle público (username)."""
        stmt = (
            select(User, Profile)
            .join(Profile, Profile.user_id == User.id)
            .where(User.username == handle, User.deleted_at.is_(None))
        )
        return (await self.db.exec(stmt)).first()

    async def get_user_by_handle(self, handle: str) -> User | None:
        stmt = select(User).where(User.username == handle, User.deleted_at.is_(None))
        return (await self.db.exec(stmt)).first()

    async def create_profile(
        self, user_id: uuid.UUID, *, display_name: str | None = None
    ) -> Profile:
        profile = Profile(user_id=user_id, display_name=display_name)
        self.db.add(profile)
        return profile

    async def update_profile(
        self, profile: Profile, *, fields: dict
    ) -> Profile:
        for key, value in fields.items():
            if value is not None:
                setattr(profile, key, value)
        profile.updated_at = utcnow()
        self.db.add(profile)
        return profile

    # ---------- Preferences (1:1, get_or_create) ----------

    async def get_preferences(self, user_id: uuid.UUID) -> ProfilePreference | None:
        stmt = select(ProfilePreference).where(ProfilePreference.user_id == user_id)
        return (await self.db.exec(stmt)).first()

    async def create_preferences(
        self, user_id: uuid.UUID
    ) -> ProfilePreference:
        pref = ProfilePreference(user_id=user_id)
        self.db.add(pref)
        return pref

    async def update_preferences(
        self, pref: ProfilePreference, *, fields: dict
    ) -> ProfilePreference:
        for key, value in fields.items():
            if value is not None:
                setattr(pref, key, value)
        pref.updated_at = utcnow()
        self.db.add(pref)
        return pref

    # ---------- Privacy (1:1, get_or_create) ----------

    async def get_privacy(self, user_id: uuid.UUID) -> PrivacySetting | None:
        stmt = select(PrivacySetting).where(PrivacySetting.user_id == user_id)
        return (await self.db.exec(stmt)).first()

    async def create_privacy(self, user_id: uuid.UUID) -> PrivacySetting:
        privacy = PrivacySetting(user_id=user_id)
        self.db.add(privacy)
        return privacy

    async def update_privacy(
        self, privacy: PrivacySetting, *, fields: dict
    ) -> PrivacySetting:
        for key, value in fields.items():
            if value is not None:
                setattr(privacy, key, value)
        privacy.updated_at = utcnow()
        self.db.add(privacy)
        return privacy

    # ---------- Reading goals ----------

    async def get_goal(self, user_id: uuid.UUID, year: int) -> ReadingGoal | None:
        stmt = select(ReadingGoal).where(
            ReadingGoal.user_id == user_id, ReadingGoal.year == year
        )
        return (await self.db.exec(stmt)).first()

    async def create_goal(
        self, user_id: uuid.UUID, year: int, *, books_goal: int | None, pages_goal: int | None
    ) -> ReadingGoal:
        goal = ReadingGoal(
            user_id=user_id, year=year, books_goal=books_goal, pages_goal=pages_goal
        )
        self.db.add(goal)
        return goal

    async def update_goal(
        self, goal: ReadingGoal, *, books_goal: int | None, pages_goal: int | None
    ) -> ReadingGoal:
        if books_goal is not None:
            goal.books_goal = books_goal
        if pages_goal is not None:
            goal.pages_goal = pages_goal
        goal.updated_at = utcnow()
        self.db.add(goal)
        return goal

    async def delete_goal(self, goal: ReadingGoal) -> None:
        await self.db.delete(goal)

    # ---------- Relaciones sociales para visibilidad (ADR-4) ----------

    async def is_following(
        self, follower_id: uuid.UUID, followee_id: uuid.UUID
    ) -> bool:
        from sqlalchemy import select as _select

        from app.social.models import Follow

        stmt = _select(Follow.id).where(
            Follow.follower_id == follower_id, Follow.followee_id == followee_id
        )
        return (await self.db.exec(stmt)).first() is not None

    async def is_blocked(self, a: uuid.UUID, b: uuid.UUID) -> bool:
        from sqlalchemy import or_ as _or_
        from sqlalchemy import select as _select

        from app.social.models import Block

        stmt = _select(Block.id).where(
            _or_(
                (Block.blocker_id == a) & (Block.blocked_id == b),
                (Block.blocker_id == b) & (Block.blocked_id == a),
            )
        )
        return (await self.db.exec(stmt)).first() is not None

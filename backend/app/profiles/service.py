"""Lógica de dominio del módulo profiles.

Reglas:
- El Profile se crea de forma perezosa (get_or_create): si un usuario ya
  existía antes de esta feature, no se toca el flujo de registro de auth.
- La lectura pública respeta `privacy_settings` vía `core.visibility`.
"""

from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.events import event_bus
from app.core.visibility import is_visible
from app.enums import Visibility
from app.profiles import events
from app.profiles.exceptions import ProfileNotFoundError, ProfilePrivateError
from app.profiles.models import PrivacySetting, Profile, ProfilePreference, ReadingGoal
from app.profiles.repository import ProfileRepository


class ProfileService:
    def __init__(self, repo: ProfileRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    # ---------- Perfil propio ----------

    async def get_or_create_own(self, user: User) -> tuple[Profile, ProfilePreference, PrivacySetting]:
        """Devuelve (y crea si falta) profile + preferences + privacy del usuario."""
        profile = await self.repo.get_by_user_id(user.id)
        if profile is None:
            profile = await self.repo.create_profile(
                user.id, display_name=user.full_name
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        pref = await self.repo.get_preferences(user.id)
        if pref is None:
            pref = await self.repo.create_preferences(user.id)
            self.db.add(pref)

        privacy = await self.repo.get_privacy(user.id)
        if privacy is None:
            privacy = await self.repo.create_privacy(user.id)
            self.db.add(privacy)

        await self.db.commit()
        await self.db.refresh(profile)
        return profile, pref, privacy

    async def update_own(
        self, user: User, *, fields: dict
    ) -> Profile:
        profile = await self.get_or_create_own(user)
        profile = await self.repo.update_profile(profile[0], fields=fields)
        await self.db.commit()
        await self.db.refresh(profile)
        await event_bus.publish(events.profile_updated(user.id))
        return profile

    async def get_own_profile(self, user: User) -> tuple[Profile, ProfilePreference, PrivacySetting]:
        return await self.get_or_create_own(user)

    # ---------- Perfil público ----------

    async def get_public(
        self, handle: str, *, viewer: User | None
    ) -> tuple[User, Profile, bool]:
        """Resuelve el perfil público de un usuario.

        Devuelve `(user, profile, is_following)` si es visible.
        Lanza `ProfileNotFoundError` si no existe y `ProfilePrivateError`
        si la privacidad no lo permite para el espectador.
        """
        target_user = await self.repo.get_user_by_handle(handle)
        if target_user is None:
            raise ProfileNotFoundError()

        profile = await self.repo.get_by_user_id(target_user.id)
        if profile is None:
            profile = await self.repo.create_profile(
                target_user.id, display_name=target_user.full_name
            )
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)

        privacy = await self.repo.get_privacy(target_user.id)
        if privacy is None:
            privacy = await self.repo.create_privacy(target_user.id)
            self.db.add(privacy)
            await self.db.commit()
            await self.db.refresh(privacy)

        viewer_id = viewer.id if viewer else None
        is_following = False
        is_blocked = False
        if viewer_id is None:
            if privacy.block_anonymous:
                raise ProfilePrivateError()
        else:
            is_following = await self.repo.is_following(viewer_id, target_user.id)
            is_blocked = await self.repo.is_blocked(viewer_id, target_user.id)

        visible = is_visible(
            privacy.profile_visibility,
            viewer_id=viewer_id,
            author_id=target_user.id,
            is_follower=is_following,
            is_blocked=is_blocked,
            author_active=target_user.is_active and target_user.deleted_at is None,
        )
        if not visible:
            raise ProfilePrivateError()

        return target_user, profile, is_following

    # ---------- Preferences ----------

    async def update_preferences(
        self, user: User, *, fields: dict
    ) -> ProfilePreference:
        pref = (await self.get_or_create_own(user))[1]
        pref = await self.repo.update_preferences(pref, fields=fields)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref

    # ---------- Privacy ----------

    async def update_privacy(self, user: User, *, fields: dict) -> PrivacySetting:
        privacy = (await self.get_or_create_own(user))[2]
        privacy = await self.repo.update_privacy(privacy, fields=fields)
        await self.db.commit()
        await self.db.refresh(privacy)
        return privacy

    # ---------- Reading goals ----------

    async def get_goal(self, user: User, year: int) -> ReadingGoal | None:
        return await self.repo.get_goal(user.id, year)

    async def upsert_goal(
        self, user: User, year: int, *, books_goal: int | None, pages_goal: int | None
    ) -> ReadingGoal:
        goal = await self.repo.get_goal(user.id, year)
        if goal is None:
            goal = await self.repo.create_goal(
                user.id, year, books_goal=books_goal, pages_goal=pages_goal
            )
            await self.db.commit()
            await self.db.refresh(goal)
            await event_bus.publish(events.reading_goal_created(user.id, goal.id, year))
        else:
            goal = await self.repo.update_goal(
                goal, books_goal=books_goal, pages_goal=pages_goal
            )
            await self.db.commit()
            await self.db.refresh(goal)
            await event_bus.publish(events.reading_goal_updated(user.id, goal.id, year))
        return goal

    async def delete_goal(self, user: User, year: int) -> bool:
        goal = await self.repo.get_goal(user.id, year)
        if goal is None:
            return False
        await self.repo.delete_goal(goal)
        await self.db.commit()
        await event_bus.publish(events.reading_goal_deleted(user.id, year))
        return True

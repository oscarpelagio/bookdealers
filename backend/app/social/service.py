"""Lógica de dominio del módulo social (FASE 4).

Reglas (documento §1.7 y FASE 4):
- No auto-follow (CHECK en BD y regla). Un Block borra Follows a dos
  sentidos (el service borra la fila y la reversa antes de crear el block).
- Un block en cualquiera de las dos direcciones impide seguir al usuario.
- `PrivacySettings.allow_follows` permite desactivar las follows entrantes.
- Las actividades son append-only; una follow genera una entrada `FOLLOWED`
  con la visibilidad del actor (copiada en el momento de crearse, ADR-4).
- Los listados públicos de actividad respetan la visibilidad de cada
  entrada y la relación de block con el espectador (ADR-4).
"""

from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.events import event_bus
from app.core.pagination import decode_cursor, encode_cursor
from app.enums import ActivityVerb, Visibility
from app.social import events
from app.social.exceptions import (
    CannotBlockSelfError,
    CannotFollowBlockedUserError,
    CannotFollowSelfError,
    CannotMuteSelfError,
    FollowsNotAllowedError,
    UserNotFoundError,
)
from app.social.models import Activity, Follow
from app.social.repository import SocialRepository
from app.social.schemas import (
    ActivityPage,
    ActivityResponse,
    FollowResponse,
    FollowingUser,
    ReportResponse,
    UserBrief,
    UserPage,
)


class SocialService:
    def __init__(self, repo: SocialRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    # ---------- Follow ----------

    async def follow(self, user: User, handle: str) -> FollowResponse:
        target = await self._resolve_handle(handle)
        if target.id == user.id:
            raise CannotFollowSelfError()

        if await self.repo.get_block_relation(user.id, target.id) is not None:
            raise CannotFollowBlockedUserError()

        privacy = await self.repo.get_privacy(target.id)
        if privacy is not None and not privacy.allow_follows:
            raise FollowsNotAllowedError()

        existing = await self.repo.get_follow(user.id, target.id)
        if existing is not None:
            return await self._follow_response(target, existing)

        follow = await self.repo.create_follow(user.id, target.id)

        # Actividad append-only (FOLLOWED), visibilidad copiada del actor.
        actor_privacy = await self.repo.get_privacy(user.id)
        visibility = (
            actor_privacy.activity_visibility
            if actor_privacy
            else Visibility.PUBLIC
        )
        await self.repo.create_activity(
            actor_id=user.id,
            verb=ActivityVerb.FOLLOWED,
            target_type="USER",
            target_id=target.id,
            visibility=visibility,
        )

        await self.db.commit()
        await self.db.refresh(follow)
        await event_bus.publish(events.follow_created(str(user.id), str(target.id)))
        return await self._follow_response(target, follow)

    async def unfollow(self, user: User, handle: str) -> None:
        target = await self._resolve_handle(handle)
        follow = await self.repo.get_follow(user.id, target.id)
        if follow is None:
            return
        await self.repo.delete_follow(follow)
        await self.db.commit()

    async def is_following(self, user: User, handle: str) -> bool:
        target = await self._resolve_handle(handle)
        return (await self.repo.get_follow(user.id, target.id)) is not None

    # ---------- Block ----------

    async def block(self, user: User, handle: str) -> None:
        target = await self._resolve_handle(handle)
        if target.id == user.id:
            raise CannotBlockSelfError()

        if await self.repo.get_block(user.id, target.id) is None:
            # Un block borra los follows a dos sentidos y crea el bloqueo.
            await self.repo.delete_follows_between(user.id, target.id)
            await self.repo.create_block(user.id, target.id)
            await self.db.commit()
            await event_bus.publish(events.block_created(str(user.id), str(target.id)))

    async def unblock(self, user: User, handle: str) -> None:
        target = await self._resolve_handle(handle)
        block = await self.repo.get_block(user.id, target.id)
        if block is None:
            return
        await self.repo.delete_block(block)
        await self.db.commit()

    # ---------- Mute ----------

    async def mute(self, user: User, handle: str) -> None:
        target = await self._resolve_handle(handle)
        if target.id == user.id:
            raise CannotMuteSelfError()
        if await self.repo.get_mute(user.id, target.id) is None:
            await self.repo.create_mute(user.id, target.id)
            await self.db.commit()
            await event_bus.publish(events.mute_created(str(user.id), str(target.id)))

    async def unmute(self, user: User, handle: str) -> None:
        target = await self._resolve_handle(handle)
        mute = await self.repo.get_mute(user.id, target.id)
        if mute is None:
            return
        await self.repo.delete_mute(mute)
        await self.db.commit()

    # ---------- Report ----------

    async def create_report(
        self, user: User, *, target_type, target_id: uuid.UUID, reason: str, details: str | None
    ) -> ReportResponse:
        report = await self.repo.create_report(
            reporter_id=user.id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            details=details,
        )
        await self.db.commit()
        await self.db.refresh(report)
        await event_bus.publish(events.report_created(str(user.id), str(report.id)))
        return ReportResponse(
            id=str(report.id),
            reporter_id=str(report.reporter_id),
            target_type=report.target_type,
            target_id=str(report.target_id),
            reason=report.reason,
            details=report.details,
            status=report.status,
            created_at=report.created_at,
        )

    # ---------- Listados de usuarios ----------

    async def followers(
        self, handle: str, viewer: User | None, *, cursor: str | None, limit: int
    ) -> UserPage:
        target = await self._resolve_handle(handle)
        if not await self._can_view_relations(target, viewer):
            return UserPage(items=[], next=None)
        after = decode_cursor(cursor)
        rows = await self.repo.list_followers(target.id, limit=limit + 1, after=after)
        return await self._paginate_users(rows, limit)

    async def following(
        self, handle: str, viewer: User | None, *, cursor: str | None, limit: int
    ) -> UserPage:
        target = await self._resolve_handle(handle)
        if not await self._can_view_relations(target, viewer):
            return UserPage(items=[], next=None)
        after = decode_cursor(cursor)
        rows = await self.repo.list_following(target.id, limit=limit + 1, after=after)
        return await self._paginate_users(rows, limit)

    # ---------- Activity ----------

    async def user_activity(
        self, handle: str, viewer: User | None, *, cursor: str | None, limit: int
    ) -> ActivityPage:
        target = await self._resolve_handle(handle)
        if not target.is_active or target.deleted_at is not None:
            return ActivityPage(items=[], next=None)

        viewer_id = viewer.id if viewer else None
        allowed: list[Visibility] | None
        if viewer_id is not None and viewer_id == target.id:
            allowed = None
        elif viewer_id is not None and await self.repo.get_block_relation(
            viewer_id, target.id
        ) is not None:
            allowed = []
        else:
            allowed = [Visibility.PUBLIC]
            if viewer_id is not None and (
                await self.repo.get_follow(viewer_id, target.id)
            ) is not None:
                allowed.append(Visibility.FOLLOWERS)

        after = decode_cursor(cursor)
        activities = await self.repo.list_activities(
            target.id, allowed=allowed, limit=limit + 1, after=after
        )
        has_more = len(activities) > limit
        page_activities = activities[:limit]
        next_cursor = None
        if has_more and page_activities:
            last = page_activities[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        actor = await self._user_brief(target)
        items = [
            self._activity_response(a, actor)
            for a in page_activities
        ]
        return ActivityPage(items=items, next=next_cursor)

    # ---------- Helpers ----------

    async def _resolve_handle(self, handle: str) -> User:
        user = await self.repo.get_user_by_handle(handle)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise UserNotFoundError()
        return user

    async def _can_view_relations(self, target: User, viewer: User | None) -> bool:
        if viewer is None:
            return True
        return (await self.repo.get_block_relation(viewer.id, target.id)) is None

    async def _follow_response(self, target: User, follow: Follow) -> FollowResponse:
        brief = await self._user_brief(target)
        return FollowResponse(followee=brief, created_at=follow.created_at)

    async def _user_brief(self, user: User) -> UserBrief:
        profiles = await self.repo.get_profiles_by_user_ids([user.id])
        profile = profiles[0] if profiles else None
        return UserBrief(
            id=str(user.id),
            username=user.username,
            display_name=profile.display_name if profile else None,
            avatar_url=profile.avatar_url if profile else None,
        )

    async def _paginate_users(
        self, rows: list[tuple[User, Follow]], limit: int
    ) -> UserPage:
        has_more = len(rows) > limit
        page = rows[:limit]
        summary: list[FollowingUser] = []
        if page:
            ids = [user.id for user, _ in page]
            profiles = {
                p.user_id: p
                for p in await self.repo.get_profiles_by_user_ids(ids)
            }
            for user, follow in page:
                profile = profiles.get(user.id)
                summary.append(
                    FollowingUser(
                        id=str(user.id),
                        username=user.username,
                        display_name=profile.display_name if profile else None,
                        avatar_url=profile.avatar_url if profile else None,
                        followed_at=follow.created_at,
                    )
                )
        next_cursor = None
        if has_more and page:
            _, last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        return UserPage(items=summary, next=next_cursor)

    def _activity_response(
        self, activity: Activity, actor: UserBrief | None
    ) -> ActivityResponse:
        return ActivityResponse(
            id=str(activity.id),
            verb=activity.verb,
            actor=actor if activity.actor_id else None,
            object_type=activity.object_type,
            object_id=str(activity.object_id) if activity.object_id else None,
            target_type=activity.target_type,
            target_id=str(activity.target_id) if activity.target_id else None,
            visibility=activity.visibility,
            created_at=activity.created_at,
        )
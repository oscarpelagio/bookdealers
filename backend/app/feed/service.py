"""Lógica de dominio del feed (FASE 5).

Reglas:
- Timeline = actividades de los usuarios seguidos + las propias.
- Se excluyen los usuarios silenciados (mute) del pool de actores.
- Los bloqueados quedan fuera por construcción: un block borra los follows
  (F4), así que nunca están en el pool de seguidos.
- Cada actividad guarda su propia visibilidad (snapshot, ADR-4); el autor
  siempre ve las suyas y el resto solo las no PRIVATE.
"""

from __future__ import annotations

import uuid

from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.core.pagination import decode_cursor, encode_cursor
from app.feed.repository import FeedRepository
from app.social.models import Activity
from app.social.schemas import ActivityPage, ActivityResponse, UserBrief


class FeedService:
    def __init__(self, repo: FeedRepository, db: AsyncSession) -> None:
        self.repo = repo
        self.db = db

    async def get_feed(
        self, user: User, *, cursor: str | None, limit: int
    ) -> ActivityPage:
        following_ids = await self.repo.get_following_ids(user.id)
        muted_ids = await self.repo.get_muted_ids(user.id)
        muted_set = set(muted_ids)

        pool = [uid for uid in following_ids if uid not in muted_set]
        if user.id not in pool:
            pool.append(user.id)

        after = decode_cursor(cursor)
        activities = await self.repo.list_feed(
            pool, user.id, limit=limit + 1, after=after
        )
        has_more = len(activities) > limit
        page_activities = activities[:limit]
        next_cursor = None
        if has_more and page_activities:
            last = page_activities[-1]
            next_cursor = encode_cursor(last.created_at, last.id)

        items = await self._responses(page_activities)
        return ActivityPage(items=items, next=next_cursor)

    async def _responses(self, activities: list[Activity]) -> list[ActivityResponse]:
        if not activities:
            return []
        actor_ids = [a.actor_id for a in activities if a.actor_id]
        users = {
            u.id: u for u in await self.repo.get_users_by_ids(actor_ids)
        }
        profiles = {
            p.user_id: p
            for p in await self.repo.get_profiles_by_user_ids(actor_ids)
        }
        briefs: dict[uuid.UUID, UserBrief] = {}
        for actor_id in set(actor_ids):
            user = users.get(actor_id)
            if user is None:
                continue
            profile = profiles.get(actor_id)
            briefs[actor_id] = UserBrief(
                id=str(actor_id),
                username=user.username,
                display_name=profile.display_name if profile else None,
                avatar_url=profile.avatar_url if profile else None,
            )

        result: list[ActivityResponse] = []
        for activity in activities:
            actor_brief = briefs.get(activity.actor_id) if activity.actor_id else None
            result.append(
                ActivityResponse(
                    id=str(activity.id),
                    verb=activity.verb,
                    actor=actor_brief,
                    object_type=activity.object_type,
                    object_id=str(activity.object_id) if activity.object_id else None,
                    target_type=activity.target_type,
                    target_id=str(activity.target_id) if activity.target_id else None,
                    visibility=activity.visibility,
                    created_at=activity.created_at,
                )
            )
        return result
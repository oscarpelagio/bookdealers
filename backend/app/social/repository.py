"""Repositorio de persistencia del módulo social.

Solo operaciones de base de datos; sin lógica de negocio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import or_
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.enums import ActivityVerb, ObjectType, ReportStatus, ReportTarget, Visibility
from app.social.models import Activity, Block, Follow, Mute, Report

if TYPE_CHECKING:
    CursorAfter = tuple[datetime, uuid.UUID] | None
else:
    CursorAfter = object


class SocialRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Users ----------

    async def get_user_by_handle(self, handle: str) -> User | None:
        stmt = select(User).where(User.username == handle)
        return (await self.db.exec(stmt)).first()

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_users_by_ids(self, ids: list[uuid.UUID]) -> list[User]:
        if not ids:
            return []
        stmt = select(User).where(User.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_actor(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    # ---------- Follow ----------

    async def get_follow(
        self, follower_id: uuid.UUID, followee_id: uuid.UUID
    ) -> Follow | None:
        stmt = select(Follow).where(
            Follow.follower_id == follower_id, Follow.followee_id == followee_id
        )
        return (await self.db.exec(stmt)).first()

    async def create_follow(
        self, follower_id: uuid.UUID, followee_id: uuid.UUID
    ) -> Follow:
        follow = Follow(follower_id=follower_id, followee_id=followee_id)
        self.db.add(follow)
        return follow

    async def delete_follow(self, follow: Follow) -> None:
        await self.db.delete(follow)

    async def list_followers(
        self, user_id: uuid.UUID, *, limit: int, after: CursorAfter
    ) -> list[tuple[User, Follow]]:
        """Usuarios que siguen a `user_id`, más la fecha del follow."""
        stmt = (
            select(User, Follow)
            .join(Follow, Follow.follower_id == User.id)
            .where(Follow.followee_id == user_id)
        )
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where((Follow.created_at, Follow.id) < (created_at, row_id))
        stmt = stmt.order_by(Follow.created_at.desc(), Follow.id.desc()).limit(limit)
        rows = (await self.db.exec(stmt)).all()
        return [(user, follow) for user, follow in rows]

    async def list_following(
        self, user_id: uuid.UUID, *, limit: int, after: CursorAfter
    ) -> list[tuple[User, Follow]]:
        """Usuarios a los que sigue `user_id`, más la fecha del follow."""
        stmt = (
            select(User, Follow)
            .join(Follow, Follow.followee_id == User.id)
            .where(Follow.follower_id == user_id)
        )
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where((Follow.created_at, Follow.id) < (created_at, row_id))
        stmt = stmt.order_by(Follow.created_at.desc(), Follow.id.desc()).limit(limit)
        rows = (await self.db.exec(stmt)).all()
        return [(user, follow) for user, follow in rows]

    # ---------- Block ----------

    async def get_block(
        self, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> Block | None:
        stmt = select(Block).where(
            Block.blocker_id == blocker_id, Block.blocked_id == blocked_id
        )
        return (await self.db.exec(stmt)).first()

    async def get_block_relation(
        self, a: uuid.UUID, b: uuid.UUID
    ) -> Block | None:
        """Devuelve un bloqueo en cualquiera de las dos direcciones."""
        stmt = select(Block).where(
            or_(
                (Block.blocker_id == a) & (Block.blocked_id == b),
                (Block.blocker_id == b) & (Block.blocked_id == a),
            )
        )
        return (await self.db.exec(stmt)).first()

    async def create_block(
        self, blocker_id: uuid.UUID, blocked_id: uuid.UUID
    ) -> Block:
        block = Block(blocker_id=blocker_id, blocked_id=blocked_id)
        self.db.add(block)
        return block

    async def delete_block(self, block: Block) -> None:
        await self.db.delete(block)

    async def delete_follows_between(self, a: uuid.UUID, b: uuid.UUID) -> None:
        """Borra follows en ambas direcciones entre dos usuarios."""
        stmt = select(Follow).where(
            or_(
                (Follow.follower_id == a) & (Follow.followee_id == b),
                (Follow.follower_id == b) & (Follow.followee_id == a),
            )
        )
        follows = (await self.db.exec(stmt)).all()
        for follow in follows:
            await self.db.delete(follow)

    # ---------- Mute ----------

    async def get_mute(self, muter_id: uuid.UUID, mutee_id: uuid.UUID) -> Mute | None:
        stmt = select(Mute).where(
            Mute.muter_id == muter_id, Mute.mutee_id == mutee_id
        )
        return (await self.db.exec(stmt)).first()

    async def create_mute(self, muter_id: uuid.UUID, mutee_id: uuid.UUID) -> Mute:
        mute = Mute(muter_id=muter_id, mutee_id=mutee_id)
        self.db.add(mute)
        return mute

    async def delete_mute(self, mute: Mute) -> None:
        await self.db.delete(mute)

    # ---------- Report ----------

    async def create_report(
        self,
        *,
        reporter_id: uuid.UUID,
        target_type: ReportTarget,
        target_id: uuid.UUID,
        reason: str,
        details: str | None,
    ) -> Report:
        report = Report(
            reporter_id=reporter_id,
            target_type=target_type,
            target_id=target_id,
            reason=reason,
            details=details,
            status=ReportStatus.OPEN,
        )
        self.db.add(report)
        return report

    # ---------- Activity ----------

    async def create_activity(
        self,
        *,
        actor_id: uuid.UUID,
        verb: ActivityVerb,
        object_type: ObjectType | None = None,
        object_id: uuid.UUID | None = None,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        visibility: Visibility,
    ) -> Activity:
        activity = Activity(
            actor_id=actor_id,
            verb=verb,
            object_type=object_type,
            object_id=object_id,
            target_type=target_type,
            target_id=target_id,
            visibility=visibility,
        )
        self.db.add(activity)
        return activity

    async def list_activities(
        self,
        actor_id: uuid.UUID,
        *,
        allowed: list[Visibility] | None,
        limit: int,
        after: CursorAfter,
    ) -> list[Activity]:
        """Lista la actividad del actor.

        `allowed` es `None` (todas) o la lista de visibilidades aceptadas.
        Si la lista está vacía no se devuelve nada (bloqueado/privado).
        """
        if allowed == []:
            return []
        stmt = select(Activity).where(Activity.actor_id == actor_id)
        if allowed is not None:
            stmt = stmt.where(Activity.visibility.in_(allowed))
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where((Activity.created_at, Activity.id) < (created_at, row_id))
        stmt = stmt.order_by(Activity.created_at.desc(), Activity.id.desc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    # ---------- Agregación para respuestas ----------

    async def get_profiles_by_user_ids(self, ids: list[uuid.UUID]) -> list:
        from app.profiles.models import Profile

        if not ids:
            return []
        stmt = select(Profile).where(Profile.user_id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_privacy(self, user_id: uuid.UUID):
        from app.profiles.models import PrivacySetting

        stmt = select(PrivacySetting).where(PrivacySetting.user_id == user_id)
        return (await self.db.exec(stmt)).first()
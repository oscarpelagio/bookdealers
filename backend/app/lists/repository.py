"""Repositorio de persistencia del módulo lists.

Solo operaciones de base de datos; sin lógica de negocio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.auth.models import User
from app.enums import ActivityVerb, Visibility
from app.lists.models import List, ListCollaborator, ListItem
from app.models import Book
from app.social.models import Activity, Follow

if TYPE_CHECKING:
    CursorAfter = tuple[datetime, uuid.UUID] | None
else:
    CursorAfter = object


class ListsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- Users / libros ----------

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_user_by_handle(self, handle: str) -> User | None:
        stmt = select(User).where(User.username == handle)
        return (await self.db.exec(stmt)).first()

    async def get_users_by_ids(self, ids: list[uuid.UUID]) -> list[User]:
        if not ids:
            return []
        stmt = select(User).where(User.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def get_book(self, book_id: int) -> Book | None:
        return await self.db.get(Book, book_id)

    async def get_books_by_ids(self, ids: list[int]) -> list[Book]:
        if not ids:
            return []
        stmt = select(Book).where(Book.id.in_(ids))
        return (await self.db.exec(stmt)).all()

    # ---------- List ----------

    async def create_list(
        self,
        *,
        owner_id: uuid.UUID,
        title: str,
        description: str | None,
        visibility: Visibility,
        slug: str,
    ) -> List:
        list_model = List(
            owner_id=owner_id,
            title=title,
            description=description,
            visibility=visibility,
            slug=slug,
        )
        self.db.add(list_model)
        await self.db.flush()
        return list_model

    async def get_list(self, list_id: uuid.UUID) -> List | None:
        return await self.db.get(List, list_id)

    async def slug_exists(self, owner_id: uuid.UUID, slug: str) -> bool:
        stmt = select(List.id).where(
            List.owner_id == owner_id, List.slug == slug, List.deleted_at.is_(None)
        )
        return (await self.db.exec(stmt)).first() is not None

    async def list_owner_lists(
        self, owner_id: uuid.UUID, *, limit: int, after: CursorAfter
    ) -> list[List]:
        stmt = select(List).where(
            List.owner_id == owner_id, List.deleted_at.is_(None)
        )
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where((List.created_at, List.id) < (created_at, row_id))
        stmt = stmt.order_by(List.created_at.desc(), List.id.desc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    async def soft_delete(self, list_model: List, deleted_at: datetime) -> None:
        list_model.deleted_at = deleted_at
        list_model.updated_at = datetime.now()

    # ---------- ListItem ----------

    async def get_item(self, list_id: uuid.UUID, book_id: int) -> ListItem | None:
        stmt = select(ListItem).where(
            ListItem.list_id == list_id, ListItem.book_id == book_id
        )
        return (await self.db.exec(stmt)).first()

    async def get_next_position(self, list_id: uuid.UUID) -> int:
        stmt = select(func.max(ListItem.position)).where(ListItem.list_id == list_id)
        max_position = (await self.db.exec(stmt)).one()
        return (max_position if max_position is not None else -1) + 1

    async def add_item(
        self,
        *,
        list_id: uuid.UUID,
        book_id: int,
        added_by: uuid.UUID,
        note: str | None,
        position: int,
    ) -> ListItem:
        item = ListItem(
            list_id=list_id,
            book_id=book_id,
            added_by=added_by,
            note=note,
            position=position,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def delete_item(self, item: ListItem) -> None:
        await self.db.delete(item)

    async def list_items(
        self, list_id: uuid.UUID, *, limit: int, after: CursorAfter
    ) -> list[ListItem]:
        stmt = select(ListItem).where(ListItem.list_id == list_id)
        if after is not None:
            created_at, row_id = after
            stmt = stmt.where((ListItem.created_at, ListItem.id) < (created_at, row_id))
        stmt = stmt.order_by(ListItem.position.asc(), ListItem.id.asc()).limit(limit)
        return (await self.db.exec(stmt)).all()

    async def count_items(self, list_id: uuid.UUID) -> int:
        stmt = select(func.count(ListItem.id)).where(ListItem.list_id == list_id)
        return (await self.db.exec(stmt)).one()

    # ---------- ListCollaborator ----------

    async def get_collaborator(
        self, list_id: uuid.UUID, user_id: uuid.UUID
    ) -> ListCollaborator | None:
        stmt = select(ListCollaborator).where(
            ListCollaborator.list_id == list_id,
            ListCollaborator.user_id == user_id,
        )
        return (await self.db.exec(stmt)).first()

    async def add_collaborator(
        self,
        *,
        list_id: uuid.UUID,
        user_id: uuid.UUID,
        role,
        can_add_books: bool,
    ) -> ListCollaborator:
        collab = ListCollaborator(
            list_id=list_id,
            user_id=user_id,
            role=role,
            can_add_books=can_add_books,
        )
        self.db.add(collab)
        await self.db.flush()
        return collab

    async def list_collaborators(
        self, list_id: uuid.UUID
    ) -> list[ListCollaborator]:
        stmt = select(ListCollaborator).where(
            ListCollaborator.list_id == list_id
        )
        return (await self.db.exec(stmt)).all()

    async def delete_collaborator(self, collab: ListCollaborator) -> None:
        await self.db.delete(collab)

    # ---------- Activity ----------

    async def create_activity(
        self,
        *,
        actor_id: uuid.UUID,
        verb: ActivityVerb,
        target_type: str | None = None,
        target_id: uuid.UUID | None = None,
        visibility: Visibility,
    ) -> Activity:
        activity = Activity(
            actor_id=actor_id,
            verb=verb,
            target_type=target_type,
            target_id=target_id,
            visibility=visibility,
        )
        self.db.add(activity)
        return activity

    # ---------- Relaciones sociales ----------

    async def get_follow(self, follower_id: uuid.UUID, followee_id: uuid.UUID) -> Follow | None:
        stmt = select(Follow).where(
            Follow.follower_id == follower_id, Follow.followee_id == followee_id
        )
        return (await self.db.exec(stmt)).first()

    async def get_block_relation(self, a: uuid.UUID, b: uuid.UUID):
        from sqlalchemy import or_

        from app.social.models import Block

        stmt = select(Block).where(
            or_(
                (Block.blocker_id == a) & (Block.blocked_id == b),
                (Block.blocker_id == b) & (Block.blocked_id == a),
            )
        )
        return (await self.db.exec(stmt)).first()

    # ---------- Agregación para respuestas ----------

    async def get_profiles_by_user_ids(self, ids: list[uuid.UUID]) -> list:
        from app.profiles.models import Profile

        if not ids:
            return []
        stmt = select(Profile).where(Profile.user_id.in_(ids))
        return (await self.db.exec(stmt)).all()

    async def count_items_by_list_ids(
        self, list_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        if not list_ids:
            return {}
        stmt = (
            select(ListItem.list_id, func.count(ListItem.id))
            .where(ListItem.list_id.in_(list_ids))
            .group_by(ListItem.list_id)
        )
        rows = (await self.db.exec(stmt)).all()
        return {list_id: count for list_id, count in rows}
